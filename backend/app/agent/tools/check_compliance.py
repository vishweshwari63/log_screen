import json
import os
import time
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.database import SessionLocal
from app.models import AgentRunLog

class CheckComplianceInput(BaseModel):
    interaction_text: str = Field(description="The full interaction text, transcript, or summary of the detailing session")
    consent_given: bool = Field(default=True, description="Consent flag indicating if active consent for data processing was retrieved")
    competitors_mentioned: List[str] = Field(default=list, description="List of competitors mentioned during the meeting")

class CheckComplianceOutput(BaseModel):
    risk_flags: List[str]
    severity: str
    detailed_analysis: str
    status: str

def run_check_compliance(input_data: CheckComplianceInput) -> CheckComplianceOutput:
    start_time = time.time()
    db = SessionLocal()
    
    text = input_data.interaction_text
    api_key = os.getenv("GROQ_API_KEY", "")
    risk_flags = []
    severity = "NONE"
    detailed_analysis = "No compliance risks detected."

    # List of rules for fallback
    # Rule 1: Off-label product claims (unproved use cases)
    off_label_detected = False
    text_lower = text.lower()
    off_label_keywords = ["cures obesity", "treats alzheimer", "cures diabetes", "off-label", "unapproved", "100% cure rate"]
    for kw in off_label_keywords:
        if kw in text_lower:
            off_label_detected = True
            risk_flags.append(f"POTENTIAL_OFF_LABEL_CLAIM: Mention of unapproved indication or keyword '{kw}'")
            severity = "HIGH"

    # Rule 2: PHI leakage without consent
    if not input_data.consent_given:
        # Check if text contains PHI indicators (names, patient IDs, phone numbers, birth dates)
        phi_keywords = ["patient name", "diagnosed with", "relative", "age", "phone number", "lives at", "dob", "ssn"]
        phi_detected = any(k in text_lower for k in phi_keywords) or "@" in text
        if phi_detected:
            risk_flags.append("PRIVACY_RISK: PHI-adjacent notes exist in transcript/summary while consent_given is False")
            severity = "HIGH" if severity != "HIGH" else "HIGH"
        else:
            risk_flags.append("CONSENT_MISSING: Interaction logged without physician consent flag")
            if severity == "NONE":
                severity = "MEDIUM"

    # Rule 3: Competitive comparison without disclaimer
    if input_data.competitors_mentioned:
        # Check if there is comparative language
        comparative_keywords = ["better than", "superior to", "safer than", "kills", "defeats", "cheaper"]
        comparative_detected = any(c in text_lower for c in comparative_keywords)
        if comparative_detected:
            risk_flags.append(f"UNSUBSTANTIATED_COMPARISON: Competitor comparisons made without disclaimer referencing clinical trials")
            if severity != "HIGH":
                severity = "MEDIUM"

    # Try LLM verification if api_key exists
    if api_key:
        try:
            llm = ChatGroq(model_name="gemma2-9b-it", groq_api_key=api_key, temperature=0.0)
            prompt = (
                "You are a pharmaceutical compliance audit assistant.\n"
                "Analyze this detailing session summary/text for risk flags.\n\n"
                f"Text: {text}\n"
                f"Consent Given: {input_data.consent_given}\n"
                f"Competitors Mentioned: {input_data.competitors_mentioned}\n\n"
                "Review these risk vectors:\n"
                "1. Off-label product claims (promoting products for unapproved usages or exaggerated statements).\n"
                "2. Missing consent flag when PHI-adjacent details exist (patient medical histories, names).\n"
                "3. Competitor claims / comparison claims that lack substantiation.\n\n"
                "Return a JSON object containing:\n"
                '- "risk_flags": List of risk strings (empty list if clear)\n'
                '- "severity": "NONE", "LOW", "MEDIUM", or "HIGH"\n'
                '- "detailed_analysis": "Explanation of risks found"\n\n'
                "Return ONLY raw JSON. No conversational remarks or markdown container."
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            cleaned_resp = response.content.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp[7:]
            if cleaned_resp.endswith("```"):
                cleaned_resp = cleaned_resp[:-3]
            cleaned_resp = cleaned_resp.strip()
            llm_result = json.loads(cleaned_resp)
            
            # Combine risk flags and select higher severity
            llm_risks = llm_result.get("risk_flags", [])
            for r in llm_risks:
                if r not in risk_flags:
                    risk_flags.append(r)
            
            llm_sev = llm_result.get("severity", "NONE")
            severity_ranking = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
            if severity_ranking.get(llm_sev, 0) > severity_ranking.get(severity, 0):
                severity = llm_sev
                
            detailed_analysis = llm_result.get("detailed_analysis", detailed_analysis)
        except Exception as e:
            print(f"Groq compliance audit failed to parse: {e}. Fallback to rule-based flags.")

    if risk_flags and detailed_analysis == "No compliance risks detected.":
        detailed_analysis = f"Flags generated by rule engine: {'; '.join(risk_flags)}"

    latency = int((time.time() - start_time) * 1000)

    # Log running of compliance tool
    run_log = AgentRunLog(
        interaction_id=None,
        tool_name="check_compliance",
        input_payload=input_data.model_dump(),
        output_payload={
            "risk_flags": risk_flags,
            "severity": severity,
            "detailed_analysis": detailed_analysis
        },
        status="SUCCESS",
        latency_ms=latency
    )
    db = SessionLocal()
    try:
        db.add(run_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving compliance log to DB: {e}")
    finally:
        db.close()

    return CheckComplianceOutput(
        risk_flags=risk_flags,
        severity=severity,
        detailed_analysis=detailed_analysis,
        status="SUCCESS"
    )
