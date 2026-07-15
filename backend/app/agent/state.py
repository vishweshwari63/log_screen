from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State representing the context of the medical representative's CRM assistant workflow.
    """
    messages: List[BaseMessage]
    user_request: str                        # The initial request or raw interaction content from the user
    hcp_id: Optional[int]                    # HCP ID associated with the request (if resolved)
    interaction_id: Optional[int]            # Interaction ID (for logging, editing, emailing, etc.)
    plan: str                                # The execution plan generated
    selected_tool: Optional[str]             # The name of the tool selected for implementation
    tool_input: Dict[str, Any]               # Arguments extracted to run the select tool
    tool_output: Dict[str, Any]              # Output response from the tool execution
    compliance_report: Dict[str, Any]        # Risk analysis flagging off-label claims, missing consent, etc.
    crm_update_status: str                   # Indicates success/failure of DB mutations
    summary: str                             # AI generated 2-3 sentence summary of the interaction
    execution_logs: List[Dict[str, Any]]     # Temporary storage of execution metrics to write to `agent_run_log`
    error: Optional[str]                     # Any error message occurred during execution
