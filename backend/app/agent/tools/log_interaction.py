import json
import os
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.database import SessionLocal
from app.models import Interaction, AgentRunLog, SentimentEnum, HCP

class LogInteractionInput(BaseModel):
    hcp_id: int = Field(description="Database ID of the Healthcare Professional")
    rep_id: str = Field(description="ID of the Medical Representative")
    raw_text: Optional[str] = Field(default=None, description="Raw transcription or text message from the interaction chat")
    structured_data: Optional[Dict[str, Any]] = Field(default=None, description="Key-value pairs of structured form data")
    mode: str = Field(default="structured", description="Mode of input: 'chat' or 'structured'")

class LogInteractionOutput(BaseModel):
    interaction_id: int
    hcp_id: int
    rep_id: str
    discussion_topics: List[str]
    products_discussed: List[str]
    samples_distributed: List[str]
    competitors_mentioned: List[str]
    objections: Optional[str]
    outcome: str
    consent_given: bool
    sentiment: str
    sentiment_confidence: float
    ai_summary: str
    raw_transcript: Optional[str]

def run_log_interaction(input_data: LogInteractionInput) -> LogInteractionOutput:
    start_time = time.time()
    db = SessionLocal()

    # Determine extraction input (shared path)
    input_content = ""
    if input_data.mode == "chat":
        input_content = f"Chat/Transcript: {input_data.raw_text}"
    else:
        input_content = f"Structured Form Data: {json.dumps(input_data.structured_data)}"

    # Call LLM via Groq
    api_key = os.getenv("GROQ_API_KEY", "")
    extracted_data = {}
    
    if api_key:
        try:
            llm = ChatGroq(model_name="gemma2-9b-it", groq_api_key=api_key, temperature=0.0)
            prompt = (
                "You are an expert CRM parser. Parse the following log interaction text "
                "or form data and extract specific information.\n\n"
                f"Input details:\n{input_content}\n\n"
                "You must return a valid JSON object matching this schema exactly:\n"
                "{\n"
                '  "discussion_topics": ["topic1", "topic2"],\n'
                '  "products_discussed": ["prod1"],\n'
                '  "samples_distributed": ["sample1"],\n'
                '  "competitors_mentioned": ["competitor1"],\n'
                '  "objections": "Any objections raised or null if none",\n'
                '  "outcome": "Brief description of the outcome",\n'
                '  "consent_given": true or false (default true unless declined),\n'
                '  "sentiment": "POSITIVE" or "NEUTRAL" or "SKEPTICAL" or "NEGATIVE",\n'
                '  "sentiment_confidence": 0.95,\n'
                '  "ai_summary": "A 2 to 3 sentence structured summary"\n'
                "}\n\n"
                "Return ONLY the raw JSON content. Do not include markdown codeblocks or extra text."
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            # Strip potential json container markdown
            cleaned_resp = response.content.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp[7:]
            if cleaned_resp.endswith("```"):
                cleaned_resp = cleaned_resp[:-3]
            cleaned_resp = cleaned_resp.strip()
            extracted_data = json.loads(cleaned_resp)
        except Exception as e:
            print(f"Groq API log_interaction error (falling back to simple parser): {e}")
            api_key = ""

    if not api_key:
        # Robust heuristic fallback
        raw_text_lower = (input_data.raw_text or "").lower()
        
        # Objections check
        objections = None
        if "skeptical" in raw_text_lower or "scared" in raw_text_lower or "fatigue" in raw_text_lower or "objection" in raw_text_lower or "complained" in raw_text_lower:
            objections = "Physician raised skepticism regarding side effects or efficacy."

        # Sentiment check
        sentiment = "NEUTRAL"
        if "great" in raw_text_lower or "good" in raw_text_lower or "excited" in raw_text_lower or "positive" in raw_text_lower:
            sentiment = "POSITIVE"
        elif "skeptical" in raw_text_lower or "doubt" in raw_text_lower or "concerned" in raw_text_lower:
            sentiment = "SKEPTICAL"
        elif "bad" in raw_text_lower or "failed" in raw_text_lower or "negative" in raw_text_lower:
            sentiment = "NEGATIVE"

        # Try to parse from structured_data if provided
        s = input_data.structured_data or {}
        extracted_data = {
            "discussion_topics": s.get("discussion_topics", ["generic product presentation"]),
            "products_discussed": s.get("products_discussed", ["Lipitor"]),
            "samples_distributed": s.get("samples_distributed", []),
            "competitors_mentioned": s.get("competitors_mentioned", []),
            "objections": s.get("objections", objections),
            "outcome": s.get("outcome", "Interaction logged successfully."),
            "consent_given": s.get("consent_given", True),
            "sentiment": s.get("sentiment", sentiment),
            "sentiment_confidence": s.get("sentiment_confidence", 0.90),
            "ai_summary": s.get("ai_summary", "Completed regular detailing visit with the customer. Discussed key product features and usage instructions.")
        }

    try:
        # Convert sentiment string to SentimentEnum
        sent_str = extracted_data.get("sentiment", "NEUTRAL").upper()
        sentiment_enum = SentimentEnum.NEUTRAL
        if sent_str in SentimentEnum.__members__:
            sentiment_enum = SentimentEnum[sent_str]

        # Insert new Interaction record
        interaction = Interaction(
            hcp_id=input_data.hcp_id,
            rep_id=input_data.rep_id,
            mode=input_data.mode,
            discussion_topics=extracted_data.get("discussion_topics", []),
            products_discussed=extracted_data.get("products_discussed", []),
            samples_distributed=extracted_data.get("samples_distributed", []),
            competitors_mentioned=extracted_data.get("competitors_mentioned", []),
            objections=extracted_data.get("objections"),
            outcome=extracted_data.get("outcome", ""),
            consent_given=extracted_data.get("consent_given", True),
            sentiment=sentiment_enum,
            sentiment_confidence=extracted_data.get("sentiment_confidence", 1.0),
            ai_summary=extracted_data.get("ai_summary", ""),
            raw_transcript=input_data.raw_text
        )
        db.add(interaction)
        db.flush() # populate interaction.id
        
        # Update HCP last_interaction_at
        hcp = db.query(HCP).filter(HCP.id == input_data.hcp_id).first()
        if hcp:
            hcp.last_interaction_at = interaction.interaction_date
            
        latency = int((time.time() - start_time) * 1000)

        # Log running of the tool
        run_log = AgentRunLog(
            interaction_id=interaction.id,
            tool_name="log_interaction",
            input_payload=input_data.model_dump(),
            output_payload={**extracted_data, "interaction_id": interaction.id},
            status="SUCCESS",
            latency_ms=latency
        )
        db.add(run_log)
        db.commit()

        return LogInteractionOutput(
            interaction_id=interaction.id,
            hcp_id=interaction.hcp_id,
            rep_id=interaction.rep_id,
            discussion_topics=interaction.discussion_topics,
            products_discussed=interaction.products_discussed,
            samples_distributed=interaction.samples_distributed,
            competitors_mentioned=interaction.competitors_mentioned,
            objections=interaction.objections,
            outcome=interaction.outcome,
            consent_given=interaction.consent_given,
            sentiment=sent_str,
            sentiment_confidence=interaction.sentiment_confidence,
            ai_summary=interaction.ai_summary,
            raw_transcript=interaction.raw_transcript
        )
    except Exception as e:
        db.rollback()
        latency = int((time.time() - start_time) * 1000)
        # Log failure
        try:
            run_log = AgentRunLog(
                interaction_id=None,
                tool_name="log_interaction",
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
