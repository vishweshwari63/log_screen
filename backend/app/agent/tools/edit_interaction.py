import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models import Interaction, AgentRunLog, SentimentEnum

class EditInteractionInput(BaseModel):
    interaction_id: int = Field(description="ID of the interaction to edit")
    updates: Dict[str, Any] = Field(description="Dict of fields to update (partial update)")

class EditInteractionOutput(BaseModel):
    interaction_id: int
    updated_fields: List[str]
    audit_trail: Dict[str, Dict[str, Any]]
    status: str

def run_edit_interaction(input_data: EditInteractionInput) -> EditInteractionOutput:
    start_time = time.time()
    db = SessionLocal()
    
    try:
        # Retrieve the existing interaction
        interaction = db.query(Interaction).filter(Interaction.id == input_data.interaction_id).first()
        if not interaction:
            raise ValueError(f"Interaction with ID {input_data.interaction_id} not found.")

        audit_trail = {}
        updated_fields = []

        # Iterate over keys in updates
        for key, new_val in input_data.updates.items():
            if not hasattr(interaction, key):
                continue
                
            old_val = getattr(interaction, key)
            
            # Format comparison for database types
            # Enums
            if key == "sentiment" and isinstance(new_val, str):
                new_val_enum = SentimentEnum[new_val.upper()] if new_val.upper() in SentimentEnum.__members__ else SentimentEnum.NEUTRAL
                if old_val != new_val_enum:
                    audit_trail[key] = {"old": old_val.name if old_val else None, "new": new_val_enum.name}
                    setattr(interaction, key, new_val_enum)
                    updated_fields.append(key)
            # Other fields (JSON list/dict compare or basic types)
            else:
                if old_val != new_val:
                    audit_trail[key] = {"old": old_val, "new": new_val}
                    setattr(interaction, key, new_val)
                    updated_fields.append(key)

        if updated_fields:
            db.flush()
        
        latency = int((time.time() - start_time) * 1000)

        # Log running of the tool, storing audit trail
        run_log = AgentRunLog(
            interaction_id=interaction.id,
            tool_name="edit_interaction",
            input_payload=input_data.model_dump(),
            output_payload={
                "status": "SUCCESS",
                "updated_fields": updated_fields,
                "audit_trail": audit_trail
            },
            status="SUCCESS",
            latency_ms=latency
        )
        db.add(run_log)
        db.commit()

        return EditInteractionOutput(
            interaction_id=interaction.id,
            updated_fields=updated_fields,
            audit_trail=audit_trail,
            status="SUCCESS"
        )
        
    except Exception as e:
        db.rollback()
        latency = int((time.time() - start_time) * 1000)
        # Log failure
        try:
            run_log = AgentRunLog(
                interaction_id=input_data.interaction_id,
                tool_name="edit_interaction",
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
