import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from sqlalchemy import or_, and_
from app.database import SessionLocal
from app.models import HCP, AgentRunLog

class SearchHCPInput(BaseModel):
    query: str = Field(description="Natural language search/filter query, e.g. 'Cardiologists in New York overdue for 3 days'")

class SearchHCPOutput(BaseModel):
    results: List[Dict[str, Any]]
    filters_applied: Dict[str, Any]
    status: str

def run_search_hcp(input_data: SearchHCPInput) -> SearchHCPOutput:
    start_time = time.time()
    db = SessionLocal()
    
    query_text = input_data.query
    api_key = os.getenv("GROQ_API_KEY", "")
    filters = {}

    if api_key:
        try:
            llm = ChatGroq(model_name="gemma2-9b-it", groq_api_key=api_key, temperature=0.0)
            prompt = (
                "You are an assistant translating natural language HCP search queries into database filters.\n"
                "Query: " + query_text + "\n\n"
                "Extract query criteria into a JSON object with keys:\n"
                "- specialization: List of strings or null\n"
                "- city: List of strings or null\n"
                "- overdue_days: Integer or null (number of days filter based on last_interaction_at)\n"
                "- name: String search filter or null\n\n"
                "Return ONLY the raw JSON content."
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            cleaned_resp = response.content.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp[7:]
            if cleaned_resp.endswith("```"):
                cleaned_resp = cleaned_resp[:-3]
            cleaned_resp = cleaned_resp.strip()
            filters = json.loads(cleaned_resp)
        except Exception as e:
            print(f"Groq API search_hcp error (falling back to local parser): {e}")
            api_key = ""

    if not api_key:
        # Fallback keyword parser
        q_lower = query_text.lower()
        specializations = []
        for spec in ["cardiology", "cardiologist", "oncology", "oncologist", "pediatrics", "pediatrician", "neurology", "neurologist", "endocrinology", "endocrinologist"]:
            if spec in q_lower:
                # normalize to model names
                if "cardio" in spec: specializations.append("Cardiology")
                elif "onco" in spec: specializations.append("Oncology")
                elif "pediatr" in spec: specializations.append("Pediatrics")
                elif "neuro" in spec: specializations.append("Neurology")
                elif "endocrin" in spec: specializations.append("Endocrinology")

        cities = []
        for city in ["chennai", "new york", "boston", "chicago", "san francisco", "phoenix"]:
            if city in q_lower:
                cities.append(city.title())

        overdue_days = None
        if "overdue" in q_lower:
            # check for numbers in the query
            words = q_lower.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    overdue_days = int(word)
                    break
            if overdue_days is None:
                overdue_days = 0 # Default indicator

        # Extract name if query does not contain specialization or city
        # or clean up common indicators in the query
        name_val = None
        import re
        clean_query = query_text
        for word in ["find", "search", "doctor", "dr.", "dr", "specialist", "hcp", "in"]:
            clean_query = re.sub(r'\b' + re.escape(word) + r'\b', '', clean_query, flags=re.IGNORECASE)

        # Clear specializations or cities if matched
        if specializations:
            for spec in ["cardiology", "cardiologist", "oncology", "oncologist", "pediatrics", "pediatrician", "neurology", "neurologist", "endocrinology", "endocrinologist"]:
                clean_query = re.sub(r'\b' + re.escape(spec) + r'\b', '', clean_query, flags=re.IGNORECASE)
        if cities:
            for city in ["chennai", "new york", "boston", "chicago", "san francisco", "phoenix"]:
                clean_query = re.sub(r'\b' + re.escape(city) + r'\b', '', clean_query, flags=re.IGNORECASE)
        if overdue_days is not None:
            clean_query = re.sub(r'\boverdue\b', '', clean_query, flags=re.IGNORECASE)
            clean_query = re.sub(r'\b\d+\b', '', clean_query)

        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        if clean_query and len(clean_query) > 1:
            name_val = clean_query

        filters = {
            "specialization": specializations if specializations else None,
            "city": cities if cities else None,
            "overdue_days": overdue_days,
            "name": name_val
        }

    try:
        # Run SQLAlchemy query based on filters
        query_obj = db.query(HCP)
        
        # Apply specialization filter
        specs = filters.get("specialization")
        if specs:
            # Support case insensitive like
            spec_filters = [HCP.specialization.ilike(f"%{s}%") for s in specs]
            query_obj = query_obj.filter(or_(*spec_filters))
            
        # Apply city filter
        cities = filters.get("city")
        if cities:
            city_filters = [HCP.city.ilike(f"%{c}%") for c in cities]
            query_obj = query_obj.filter(or_(*city_filters))
            
        # Apply overdue filter (last_interaction_at is older than target date OR last_interaction_at is Null)
        overdue_days = filters.get("overdue_days")
        if overdue_days is not None:
            overdue_date = datetime.utcnow() - timedelta(days=int(overdue_days))
            query_obj = query_obj.filter(
                or_(
                    HCP.last_interaction_at == None,
                    HCP.last_interaction_at <= overdue_date
                )
            )

        # Apply name filter
        name = filters.get("name")
        if name:
            query_obj = query_obj.filter(HCP.name.ilike(f"%{name}%"))

        hcps = query_obj.all()
        
        # Format results
        results = []
        for h in hcps:
            results.append({
                "id": h.id,
                "name": h.name,
                "specialization": h.specialization,
                "hospital": h.hospital,
                "city": h.city,
                "phone": h.phone,
                "email": h.email,
                "preferred_products": h.preferred_products,
                "relationship_score": h.relationship_score,
                "last_interaction_at": h.last_interaction_at.isoformat() if h.last_interaction_at else None
            })

        latency = int((time.time() - start_time) * 1000)

        # Log running of the tool
        run_log = AgentRunLog(
            interaction_id=None,
            tool_name="search_hcp",
            input_payload=input_data.model_dump(),
            output_payload={
                "results_count": len(results),
                "filters_applied": filters
            },
            status="SUCCESS",
            latency_ms=latency
        )
        db.add(run_log)
        db.commit()

        return SearchHCPOutput(
            results=results,
            filters_applied=filters,
            status="SUCCESS"
        )
        
    except Exception as e:
        db.rollback()
        latency = int((time.time() - start_time) * 1000)
        # Log failure
        try:
            run_log = AgentRunLog(
                interaction_id=None,
                tool_name="search_hcp",
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
