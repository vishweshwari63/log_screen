import json
import os
import time
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# Import state and tools
from app.agent.state import AgentState
from app.agent.tools.log_interaction import run_log_interaction, LogInteractionInput
from app.agent.tools.edit_interaction import run_edit_interaction, EditInteractionInput
from app.agent.tools.search_hcp import run_search_hcp, SearchHCPInput
from app.agent.tools.generate_followup_email import run_generate_followup_email, GenerateFollowupEmailInput
from app.agent.tools.check_compliance import run_check_compliance, CheckComplianceInput

from app.database import SessionLocal
from app.models import AgentRunLog

# ----------------- NODES IMPLEMENTATION -----------------

def understand_request_node(state: AgentState) -> Dict[str, Any]:
    print("[Node] understand_request")
    user_req = state.get("user_request", "")
    api_key = os.getenv("GROQ_API_KEY", "")
    
    parsed = {}
    if api_key:
        try:
            llm = ChatGroq(model_name="gemma2-9b-it", groq_api_key=api_key, temperature=0.0)
            prompt = (
                "You are an assistant routing a medical representative's CRM query.\n"
                f"Query: '{user_req}'\n\n"
                "Classify the query into one of these tools:\n"
                "1. 'log_interaction' -> logging a new visit. Input contains hcp_id, rep_id, and raw_text OR structured_data.\n"
                "2. 'edit_interaction' -> correcting/modifying an existing interaction. Input contains interaction_id, and dict of field updates.\n"
                "3. 'search_hcp' -> searching for doctors. Input contains query (natural language string).\n"
                "4. 'generate_followup_email' -> drafting email. Input contains interaction_id.\n"
                "5. 'check_compliance' -> scanning for risks. Input contains interaction_text.\n\n"
                "Return a JSON object with keys:\n"
                "- selected_tool: string (one of the 5 tools above)\n"
                "- tool_input: dictionary of args matching the selected tool's schema\n"
                "- plan: short sentence describing the steps to take\n\n"
                "Return ONLY raw JSON."
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            cleaned_resp = response.content.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp[7:]
            if cleaned_resp.endswith("```"):
                cleaned_resp = cleaned_resp[:-3]
            cleaned_resp = cleaned_resp.strip()
            parsed = json.loads(cleaned_resp)
        except Exception as e:
            print(f"Groq router failed, falling back: {e}")
            api_key = ""

    if not api_key:
        # Fallback local router
        req_lower = user_req.lower()
        if "email" in req_lower or "draft" in req_lower or "send" in req_lower:
            # try to find numbers for interaction_id
            int_id = 1
            for word in req_lower.split():
                if word.isdigit():
                    int_id = int(word)
                    break
            parsed = {
                "selected_tool": "generate_followup_email",
                "tool_input": {"interaction_id": int_id},
                "plan": "Draft a follow-up email for the interaction."
            }
        elif "edit" in req_lower or "update" in req_lower or "correct" in req_lower or "change" in req_lower:
            int_id = 1
            for word in req_lower.split():
                if word.isdigit():
                    int_id = int(word)
                    break
            # default updates for parsing
            updates = {}
            if "outcome" in req_lower:
                updates["outcome"] = "Updated outcome notes as requested."
            if "consent" in req_lower:
                updates["consent_given"] = True
            parsed = {
                "selected_tool": "edit_interaction",
                "tool_input": {"interaction_id": int_id, "updates": updates},
                "plan": "Edit the selected interaction with requested changes."
            }
        elif len(user_req) < 100 and ("search" in req_lower or "find" in req_lower or "doctor" in req_lower or "cardiologist" in req_lower or "oncologist" in req_lower or "specialist" in req_lower):
            parsed = {
                "selected_tool": "search_hcp",
                "tool_input": {"query": user_req},
                "plan": "Translate natural query into HCP database filters."
            }
        elif "compliance" in req_lower or "audit" in req_lower or "risk" in req_lower or "off-label" in req_lower:
            parsed = {
                "selected_tool": "check_compliance",
                "tool_input": {"interaction_text": user_req},
                "plan": "Run compliance risk analysis on text transcript."
            }
        else:
            # Default to log_interaction
            hcp_id = 1
            for word in req_lower.split():
                if word.isdigit():
                    hcp_id = int(word)
                    break
            parsed = {
                "selected_tool": "log_interaction",
                "tool_input": {
                    "hcp_id": hcp_id, 
                    "rep_id": "rep_999", 
                    "raw_text": user_req,
                    "mode": "chat" if "chat" in req_lower or len(user_req) > 50 else "structured"
                },
                "plan": "Initialize detailing session logging using provided interaction details."
            }

    return {
        "selected_tool": parsed.get("selected_tool"),
        "tool_input": parsed.get("tool_input", {}),
        "plan": parsed.get("plan", "Perform CRM log/query processing.")
    }

def plan_node(state: AgentState) -> Dict[str, Any]:
    print(f"[Node] plan: {state.get('plan')}")
    # Simple pass-through or enhancement of plan
    plan_desc = state.get("plan", "")
    return {"plan": f"Plan approved: {plan_desc}"}

def select_tool_node(state: AgentState) -> Dict[str, Any]:
    tool_name = state.get("selected_tool")
    print(f"[Node] select_tool: {tool_name}")
    return {"selected_tool": tool_name}

def execute_tool_node(state: AgentState) -> Dict[str, Any]:
    tool_name = state.get("selected_tool")
    tool_input = state.get("tool_input", {})
    print(f"[Node] execute_tool: {tool_name} with {tool_input}")
    
    output_dict = {}
    err = None
    try:
        if tool_name == "log_interaction":
            res = run_log_interaction(LogInteractionInput(**tool_input))
            output_dict = res.model_dump()
        elif tool_name == "edit_interaction":
            res = run_edit_interaction(EditInteractionInput(**tool_input))
            output_dict = res.model_dump()
        elif tool_name == "search_hcp":
            res = run_search_hcp(SearchHCPInput(**tool_input))
            output_dict = res.model_dump()
        elif tool_name == "generate_followup_email":
            res = run_generate_followup_email(GenerateFollowupEmailInput(**tool_input))
            output_dict = res.model_dump()
        elif tool_name == "check_compliance":
            res = run_check_compliance(CheckComplianceInput(**tool_input))
            output_dict = res.model_dump()
        else:
            raise ValueError(f"Unknown tool name: {tool_name}")
    except Exception as e:
        err = str(e)
        output_dict = {"status": "FAILED", "error": err}
        print(f"Tool execution failed: {e}")

    return {
        "tool_output": output_dict, 
        "error": err,
        # Set hcp_id or interaction_id in state if outputted
        "interaction_id": output_dict.get("interaction_id", state.get("interaction_id")),
        "hcp_id": output_dict.get("hcp_id", state.get("hcp_id"))
    }

def update_crm_node(state: AgentState) -> Dict[str, Any]:
    print("[Node] update_crm")
    tool_name = state.get("selected_tool")
    tool_output = state.get("tool_output", {})
    
    # If a new interaction was logged, run implicit compliance scan automatically!
    compliance_report = {}
    if tool_name == "log_interaction" and tool_output.get("status") != "FAILED":
        print("Implicit compliance post-check active...")
        try:
            raw_text = tool_output.get("raw_transcript") or tool_output.get("ai_summary", "")
            comp_input = CheckComplianceInput(
                interaction_text=raw_text,
                consent_given=tool_output.get("consent_given", True),
                competitors_mentioned=tool_output.get("competitors_mentioned", [])
            )
            comp_res = run_check_compliance(comp_input)
            compliance_report = comp_res.model_dump()
        except Exception as e:
            print(f"Implicit compliance check failed: {e}")

    return {
        "crm_update_status": "SUCCESS" if not state.get("error") else "FAILED",
        "compliance_report": compliance_report
    }

def generate_summary_node(state: AgentState) -> Dict[str, Any]:
    print("[Node] generate_summary")
    tool_name = state.get("selected_tool")
    tool_output = state.get("tool_output", {})
    
    summary = ""
    if state.get("error"):
        summary = f"Operation failed: {state.get('error')}"
    elif tool_name == "log_interaction":
        summary = f"Logged interaction {tool_output.get('interaction_id')} covering {', '.join(tool_output.get('products_discussed', []))}. Sentiment: {tool_output.get('sentiment')}."
    elif tool_name == "edit_interaction":
        summary = f"Updated interaction {tool_output.get('interaction_id')}. Changed fields: {', '.join(tool_output.get('updated_fields', []))}."
    elif tool_name == "search_hcp":
        summary = f"Search returned {len(tool_output.get('results', []))} HCPs matching filters: {tool_output.get('filters_applied')}."
    elif tool_name == "generate_followup_email":
        summary = f"Follow-up email generated for {tool_output.get('recipient_email')}. Draft saved."
    elif tool_name == "check_compliance":
        summary = f"Compliance audit completed with rating {tool_output.get('severity')}. Flags raised: {len(tool_output.get('risk_flags', []))}."

    return {"summary": summary}

def save_data_node(state: AgentState) -> Dict[str, Any]:
    print("[Node] save_data")
    # Save overall graph execution details
    db = SessionLocal()
    try:
        run_log = AgentRunLog(
            interaction_id=state.get("interaction_id"),
            tool_name="LangGraph_Workflow",
            input_payload={
                "user_request": state.get("user_request"),
                "selected_tool": state.get("selected_tool"),
                "plan": state.get("plan")
            },
            output_payload={
                "summary": state.get("summary"),
                "crm_update_status": state.get("crm_update_status"),
                "compliance_report": state.get("compliance_report")
            },
            status="SUCCESS" if not state.get("error") else "FAILED",
            latency_ms=100, # Mock workflow logic overhead latency
            created_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.add(run_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving workflow status to DB: {e}")
    finally:
        db.close()
    return {}

def complete_node(state: AgentState) -> Dict[str, Any]:
    print("[Node] complete")
    return {}

# ----------------- GRAPH CONSTRUCTION -----------------

builder = StateGraph(AgentState)

builder.add_node("understand_request", understand_request_node)
builder.add_node("plan", plan_node)
builder.add_node("select_tool", select_tool_node)
builder.add_node("execute_tool", execute_tool_node)
builder.add_node("update_crm", update_crm_node)
builder.add_node("generate_summary", generate_summary_node)
builder.add_node("save_data", save_data_node)
builder.add_node("complete", complete_node)

builder.set_entry_point("understand_request")
builder.add_edge("understand_request", "plan")
builder.add_edge("plan", "select_tool")
builder.add_edge("select_tool", "execute_tool")
builder.add_edge("execute_tool", "update_crm")
builder.add_edge("update_crm", "generate_summary")
builder.add_edge("generate_summary", "save_data")
builder.add_edge("save_data", "complete")
builder.add_edge("complete", END)

# Compile graph
graph = builder.compile()
