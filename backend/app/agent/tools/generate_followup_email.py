import os
import time
from typing import Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.database import SessionLocal
from app.models import Interaction, HCP, AgentRunLog

class GenerateFollowupEmailInput(BaseModel):
    interaction_id: int = Field(description="ID of the interaction to generate the follow-up email for")

class GenerateFollowupEmailOutput(BaseModel):
    interaction_id: int
    email_subject: str
    email_body: str
    recipient_email: str
    status: str

def run_generate_followup_email(input_data: GenerateFollowupEmailInput) -> GenerateFollowupEmailOutput:
    start_time = time.time()
    db = SessionLocal()
    
    try:
        # Retrieve the interaction
        interaction = db.query(Interaction).filter(Interaction.id == input_data.interaction_id).first()
        if not interaction:
            raise ValueError(f"Interaction with ID {input_data.interaction_id} not found.")
            
        # Retrieve associated HCP details
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        if not hcp:
            raise ValueError(f"HCP associated with interaction {input_data.interaction_id} not found.")

        # Prepare details for drafting email
        topics = ", ".join(interaction.discussion_topics) if interaction.discussion_topics else "recent medical developments"
        products = ", ".join(interaction.products_discussed) if interaction.products_discussed else "our product offerings"
        outcome = interaction.outcome
        hcp_name = hcp.name
        
        api_key = os.getenv("GROQ_API_KEY", "")
        email_subject = f"Follow-up: Detailing Discussion regarding {products}"
        email_body = ""

        if api_key:
            try:
                # Use Llama-3.3-70b-versatile for long-form quality generation
                llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key, temperature=0.7)
                prompt = (
                    "You are a professional Medical Representative writing a follow-up email to a healthcare provider.\n\n"
                    f"Recipient: {hcp_name}\n"
                    f"Products Discussed: {products}\n"
                    f"Topics Covered: {topics}\n"
                    f"Agreed Outcome / Next Steps: {outcome}\n\n"
                    "Write a professional, polite, and compliant follow-up email. Do not mention generic placeholders. "
                    "Confirm the next steps agreed in the outcome. Sign off as 'Your Medical Detailing Team'.\n\n"
                    "Provide ONLY the email body. Do not include subject lines or conversational remarks before/after the email."
                )
                response = llm.invoke([HumanMessage(content=prompt)])
                email_body = response.content.strip()
            except Exception as e:
                print(f"Groq API generate_followup_email error (falling back to local generator): {e}")
                api_key = ""

        if not api_key:
            # Local fallback generator
            email_body = (
                f"Dear {hcp_name},\n\n"
                f"Thank you for taking the time to meet with me. I appreciate our discussion regarding {topics} "
                f"and our latest findings for {products}.\n\n"
                f"As we discussed, here is the agreed outcome: {outcome}.\n\n"
                f"Please let me know if you need any additional clinical documentation or samples.\n\n"
                f"Best regards,\nYour Medical Detailing Team"
            )

        latency = int((time.time() - start_time) * 1000)

        # Log running of the tool
        run_log = AgentRunLog(
            interaction_id=interaction.id,
            tool_name="generate_followup_email",
            input_payload=input_data.model_dump(),
            output_payload={
                "email_subject": email_subject,
                "email_body": email_body,
                "recipient": hcp.email
            },
            status="SUCCESS",
            latency_ms=latency
        )
        db.add(run_log)
        db.commit()

        return GenerateFollowupEmailOutput(
            interaction_id=interaction.id,
            email_subject=email_subject,
            email_body=email_body,
            recipient_email=hcp.email,
            status="SUCCESS"
        )
        
    except Exception as e:
        db.rollback()
        latency = int((time.time() - start_time) * 1000)
        # Log failure
        try:
            run_log = AgentRunLog(
                interaction_id=input_data.interaction_id,
                tool_name="generate_followup_email",
                input_payload=input_data.model_dump(),
                output_payload={"error": str(e)},
                status="FAILED",
                latency_ms=latency
            )
            db.add(run_log)
            db.commit()
        except:
            pass
        raise e
    finally:
        db.close()
