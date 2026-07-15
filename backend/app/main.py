import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.database import SessionLocal, get_db
from app.models import AgentRunLog, Interaction, HCP
from app.agent.graph import graph
from app.agent.tools.edit_interaction import run_edit_interaction, EditInteractionInput
from app.agent.tools.search_hcp import run_search_hcp, SearchHCPInput
from app.agent.tools.generate_followup_email import run_generate_followup_email, GenerateFollowupEmailInput
from app.agent.tools.check_compliance import run_check_compliance, CheckComplianceInput

app = FastAPI(title="HCP CRM AI Detailing Backend API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- SCHEMAS -----------------

class InteractionLogInput(BaseModel):
    hcp_id: int
    rep_id: str
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    mode: str = "structured"  # "chat" or "structured"

class EditInteractionAPIInput(BaseModel):
    updates: Dict[str, Any]

# ----------------- ENDPOINTS -----------------

@app.post("/api/interactions/log")
async def log_interaction_endpoint(payload: InteractionLogInput, db = Depends(get_db)):
    """
    Log a new interaction. Invokes the LangGraph agent and returns results + execution logs trace.
    """
    state_input = {
        "user_request": payload.raw_text if payload.mode == "chat" else f"Log structured data: {json.dumps(payload.structured_data)}",
        "hcp_id": payload.hcp_id,
        "rep_id": payload.rep_id,
        "messages": [],
        "plan": "",
        "selected_tool": "log_interaction",
        "tool_input": {
            "hcp_id": payload.hcp_id,
            "rep_id": payload.rep_id,
            "raw_text": payload.raw_text,
            "structured_data": payload.structured_data,
            "mode": payload.mode
        },
        "tool_output": {},
        "compliance_report": {},
        "crm_update_status": "",
        "summary": "",
        "execution_logs": []
    }
    
    try:
        # Invoke LangGraph Graph sync
        loop = asyncio.get_event_loop()
        result_state = await loop.run_in_executor(None, graph.invoke, state_input)
        
        interaction_id = result_state.get("interaction_id")
        
        # Query DB tool trace for this run
        trace = []
        if interaction_id:
            db_logs = db.query(AgentRunLog).filter(AgentRunLog.interaction_id == interaction_id).order_by(AgentRunLog.created_at.asc()).all()
            for l in db_logs:
                trace.append({
                    "id": l.id,
                    "tool_name": l.tool_name,
                    "input_payload": l.input_payload,
                    "output_payload": l.output_payload,
                    "status": l.status,
                    "latency_ms": l.latency_ms,
                    "created_at": l.created_at.isoformat() if hasattr(l.created_at, "isoformat") else str(l.created_at)
                })

        return {
            "status": "SUCCESS" if not result_state.get("error") else "FAILED",
            "interaction_id": interaction_id,
            "summary": result_state.get("summary"),
            "compliance_report": result_state.get("compliance_report"),
            "crm_update_status": result_state.get("crm_update_status"),
            "plan": result_state.get("plan"),
            "tool_output": result_state.get("tool_output"),
            "trace": trace
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/interactions/{id}")
async def edit_interaction_endpoint(id: int, payload: EditInteractionAPIInput):
    """
    Invokes edit_interaction tool to update selected elements and construct old->new audit log.
    """
    try:
        tool_input = EditInteractionInput(interaction_id=id, updates=payload.updates)
        # Execute tool
        result = run_edit_interaction(tool_input)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hcps")
async def search_hcp_endpoint(query: str = Query(..., description="Query terms to search HCP databases")):
    """
    Invokes search_hcp tool to translate natural prompt into SQL filters.
    """
    try:
        tool_input = SearchHCPInput(query=query)
        result = run_search_hcp(tool_input)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interactions/{id}/followup-email")
async def generate_email_endpoint(id: int):
    """
    Invokes generate_followup_email based on past interaction.
    """
    try:
        tool_input = GenerateFollowupEmailInput(interaction_id=id)
        result = run_generate_followup_email(tool_input)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interactions/{id}/compliance-check")
async def compliance_endpoint(id: int, db = Depends(get_db)):
    """
    Retrieves interaction content and runs check_compliance on it.
    """
    interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
        
    try:
        text_content = interaction.raw_transcript or interaction.ai_summary or ""
        tool_input = CheckComplianceInput(
            interaction_text=text_content,
            consent_given=interaction.consent_given,
            competitors_mentioned=interaction.competitors_mentioned
        )
        result = run_check_compliance(tool_input)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interactions/{id}/agent-trace")
async def get_agent_trace_endpoint(id: int, db = Depends(get_db)):
    """
    Returns node-by-node trace of tool runs for animated display.
    """
    logs = db.query(AgentRunLog).filter(AgentRunLog.interaction_id == id).order_by(AgentRunLog.created_at.asc()).all()
    
    trace_nodes = []
    for log in logs:
        trace_nodes.append({
            "id": log.id,
            "tool_name": log.tool_name,
            "input_payload": log.input_payload,
            "output_payload": log.output_payload,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat() if hasattr(log.created_at, "isoformat") else str(log.created_at)
        })
    return {"trace": trace_nodes}

# ----------------- SSE STREAMING -----------------

@app.get("/api/interactions/stream")
async def stream_agent_steps(
    user_request: str, 
    hcp_id: int, 
    rep_id: str, 
    mode: str = "structured"
):
    """
    Streams LangGraph execution node-by-node via Server-Sent Events (SSE).
    Powers real-time "AI thinking" animated progress UI on the frontend.
    """
    async def sse_generator():
        # Initialize graph inputs
        state_input = {
            "user_request": user_request,
            "hcp_id": hcp_id,
            "rep_id": rep_id,
            "messages": [],
            "plan": "",
            "selected_tool": None,
            "tool_input": {},
            "tool_output": {},
            "compliance_report": {},
            "crm_update_status": "",
            "summary": "",
            "execution_logs": []
        }
        
        loop = asyncio.get_event_loop()
        
        yield {
            "event": "node_start",
            "data": json.dumps({"node": "entry", "message": "Initializing Graph..."})
        }
        
        try:
            # We run graph.astream in background using executor or running its generator
            # LangGraph standard graph.stream() yields steps
            # Since graph.stream runs synchronous IO in tools, we run it in an executor and yield values
            def run_sync_stream():
                return list(graph.stream(state_input))
                
            steps = await loop.run_in_executor(None, run_sync_stream)
            
            for step in steps:
                # step is a dictionary of node_name -> output_states
                for node_name, output in step.items():
                    node_output = output or {}
                    yield {
                        "event": "node",
                        "data": json.dumps({
                            "node": node_name,
                            "summary": node_output.get("summary", ""),
                            "crm_update_status": node_output.get("crm_update_status", ""),
                            "compliance_report": node_output.get("compliance_report", {}),
                            "selected_tool": node_output.get("selected_tool", ""),
                            "plan": node_output.get("plan", ""),
                            "interaction_id": node_output.get("interaction_id")
                        })
                    }
                    # Small delay to simulate smooth network animation stream
                    await asyncio.sleep(0.5)

            yield {
                "event": "complete",
                "data": json.dumps({"message": "Workflow completed successfully."})
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)})
            }

    return EventSourceResponse(sse_generator())
