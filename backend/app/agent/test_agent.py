import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.agent.graph import graph
from app.database import SessionLocal
from app.models import AgentRunLog, Interaction, HCP

def run_test():
    print("Initializing test run on LangGraph CRM Agent...")
    
    # 1. Test Search HCP
    print("\n--- Test Case 1: Search HCP ---")
    state_input1 = {
        "user_request": "Find cardiologists in New York",
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
    result1 = graph.invoke(state_input1)
    print(f"Plan: {result1.get('plan')}")
    print(f"Selected Tool: {result1.get('selected_tool')}")
    print(f"Summary: {result1.get('summary')}")
    print(f"CRM Update Status: {result1.get('crm_update_status')}")
    
    # 2. Test Log Interaction
    print("\n--- Test Case 2: Log Interaction ---")
    state_input2 = {
        "user_request": "Log a conversation with Dr. Sarah Smith (ID 2). We discussed Keytruda combination. The discussion went very well, outcome is follow up next week. Consent was given.",
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
    result2 = graph.invoke(state_input2)
    print(f"Plan: {result2.get('plan')}")
    print(f"Selected Tool: {result2.get('selected_tool')}")
    print(f"Summary: {result2.get('summary')}")
    print(f"CRM Update Status: {result2.get('crm_update_status')}")
    print(f"Implicit compliance check report: {result2.get('compliance_report')}")

    # 3. Test Generate Email
    print("\n--- Test Case 3: Email Generation ---")
    # Retrieve the latest interaction logged to use its ID
    db = SessionLocal()
    latest_interaction = db.query(Interaction).order_by(Interaction.id.desc()).first()
    db.close()
    
    int_id = latest_interaction.id if latest_interaction else 1
    state_input3 = {
        "user_request": f"Draft a follow-up email for interaction {int_id}",
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
    result3 = graph.invoke(state_input3)
    print(f"Plan: {result3.get('plan')}")
    print(f"Selected Tool: {result3.get('selected_tool')}")
    print(f"Summary: {result3.get('summary')}")
    print(f"Email body preview:\n{result3.get('tool_output', {}).get('email_body')}")

    # 4. Verification of database logs
    print("\n--- DB Logging Verification ---")
    db = SessionLocal()
    logs = db.query(AgentRunLog).order_by(AgentRunLog.id.desc()).limit(10).all()
    print(f"Total retrieved agent run logs: {len(logs)}")
    for log in logs:
        print(f"Log ID: {log.id} | Tool: {log.tool_name} | Status: {log.status} | Latency: {log.latency_ms}ms")
    db.close()

if __name__ == "__main__":
    run_test()
