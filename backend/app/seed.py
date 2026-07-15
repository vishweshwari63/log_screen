import os
import sys
from datetime import datetime, timedelta

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, engine
from app.models import Base, HCP, Interaction, FollowUp, AgentRunLog, SentimentEnum

def seed_db():
    print("Connecting to database to seed data...")
    db = SessionLocal()
    try:
        # Clear existing seed data (order respects Foreign Key relations)
        print("Clearing existing data...")
        db.query(FollowUp).delete()
        db.query(AgentRunLog).delete()
        db.query(Interaction).delete()
        db.query(HCP).delete()
        db.commit()

        print("Adding sample Healthcare Professionals (HCPs)...")
        hcp1 = HCP(
            name="Dr. John Doe",
            specialization="Cardiology",
            hospital="Metro Hospital",
            city="New York",
            phone="+1-555-0199",
            email="john.doe@metro.com",
            preferred_products=["Lipitor", "Crestor"],
            relationship_score=8.5,
            last_interaction_at=datetime.utcnow() - timedelta(days=4)
        )
        hcp2 = HCP(
            name="Dr. Sarah Smith",
            specialization="Oncology",
            hospital="City Cancer Center",
            city="Boston",
            phone="+1-555-0188",
            email="sarah.smith@citycancer.org",
            preferred_products=["Keytruda"],
            relationship_score=9.0,
            last_interaction_at=datetime.utcnow() - timedelta(days=2)
        )
        hcp3 = HCP(
            name="Dr. Alice Johnson",
            specialization="Pediatrics",
            hospital="Children's Health",
            city="Chicago",
            phone="+1-555-0177",
            email="alice.j@childrenshealth.org",
            preferred_products=["Albuterol", "Amoxicillin"],
            relationship_score=7.2,
            last_interaction_at=None
        )
        hcp4 = HCP(
            name="Dr. Robert Lee",
            specialization="Neurology",
            hospital="Neuro Care Inst",
            city="San Francisco",
            phone="+1-555-0166",
            email="rlee@neurocare.org",
            preferred_products=["Avanex", "Tysabri"],
            relationship_score=6.8,
            last_interaction_at=datetime.utcnow() - timedelta(days=1)
        )
        hcp5 = HCP(
            name="Dr. Emily Davis",
            specialization="Endocrinology",
            hospital="Valley Medical",
            city="Phoenix",
            phone="+1-555-0155",
            email="edavis@valleymed.com",
            preferred_products=["Humalog", "Jardiance"],
            relationship_score=8.0,
            last_interaction_at=None
        )

        db.add_all([hcp1, hcp2, hcp3, hcp4, hcp5])
        db.flush() # Flush to populate generated IDs for Foreign Keys

        print("Adding sample Interactions...")
        
        # Interaction 1: Structured Cardiology Interaction with John Doe
        int1 = Interaction(
            hcp_id=hcp1.id,
            rep_id="rep_999",
            interaction_date=datetime.utcnow() - timedelta(days=4),
            mode="structured",
            discussion_topics=["efficacy of Lipitor vs generics", "dosage updates"],
            products_discussed=["Lipitor"],
            samples_distributed=["Lipitor 10mg - 10 packs"],
            competitors_mentioned=["Zocor (Merck)"],
            objections="Dr. Doe was skeptical about prescribing Lipitor due to recent concerns on generic efficacy, but after reviewing trials, he was satisfied.",
            outcome="Agreed to trial Lipitor for 10 new patients.",
            consent_given=True,
            sentiment=SentimentEnum.POSITIVE,
            sentiment_confidence=0.92,
            ai_summary="Discussed Lipitor efficacy compared to generic alternatives. Provided 10 sample packs of Lipitor 10mg. Doc was receptive post trial review.",
            raw_transcript=None
        )

        # Interaction 2: Chat Oncology Interaction with Sarah Smith
        int2 = Interaction(
            hcp_id=hcp2.id,
            rep_id="rep_999",
            interaction_date=datetime.utcnow() - timedelta(days=2),
            mode="chat",
            discussion_topics=["Keytruda safety profiling in combination therapies"],
            products_discussed=["Keytruda"],
            samples_distributed=[],
            competitors_mentioned=["Opdivo"],
            objections=None,
            outcome="Requested follow-up meeting with oncology clinical specialist.",
            consent_given=True,
            sentiment=SentimentEnum.NEUTRAL,
            sentiment_confidence=0.88,
            ai_summary="Conversational discussion on Keytruda. Discussed Opdivo profile differences. Follow-up meeting scheduled.",
            raw_transcript="Rep: Hi Dr. Smith, how is Keytruda performing for you? Dr. Smith: Quite well, though we are looking at combination therapies. Rep: Excellent, our data on combinations looks very promising. Dr. Smith: Send me the docs or schedule a quick synch."
        )

        # Interaction 3: Structured Neurology Interaction with Robert Lee
        int3 = Interaction(
            hcp_id=hcp4.id,
            rep_id="rep_888",
            interaction_date=datetime.utcnow() - timedelta(days=1),
            mode="structured",
            discussion_topics=["Avanex side effects profiling"],
            products_discussed=["Avanex"],
            samples_distributed=[],
            competitors_mentioned=[],
            objections="Expressed strong concerns about patient fatigue as a side effect. Felt other alternatives are safer.",
            outcome="Requires medical team documentation on fatigue management.",
            consent_given=False,
            sentiment=SentimentEnum.NEGATIVE,
            sentiment_confidence=0.85,
            ai_summary="Dr. Lee was skeptical about Avanex due to patient fatigue issues. Did not give consent to store detailed transcript. Ordered medical info.",
            raw_transcript=None
        )

        db.add_all([int1, int2, int3])
        db.flush()

        print("Adding sample Follow-ups...")
        fu1 = FollowUp(
            interaction_id=int2.id,
            due_date=datetime.utcnow() + timedelta(days=5),
            status="PENDING",
            notes="Schedule follow-up meeting with clinical specialist and email them the combination trial documents."
        )
        fu2 = FollowUp(
            interaction_id=int3.id,
            due_date=datetime.utcnow() + timedelta(days=2),
            status="PENDING",
            notes="Submit query to MSL (Medical Science Liaison) team regarding fatigue management data."
        )
        db.add_all([fu1, fu2])

        print("Adding sample Agent Run Logs (to demonstrate tool outputs)...")
        log1 = AgentRunLog(
            interaction_id=int2.id,
            tool_name="sentiment_analyzer",
            input_payload={"transcript": int2.raw_transcript},
            output_payload={"sentiment": "NEUTRAL", "confidence": 0.88, "status": "analyzed"},
            status="SUCCESS",
            latency_ms=325
        )
        log2 = AgentRunLog(
            interaction_id=int2.id,
            tool_name="summarize_transcript",
            input_payload={"transcript": int2.raw_transcript},
            output_payload={"summary": "Conversational discussion on Keytruda. Discussed Opdivo profile differences. Follow-up meeting scheduled."},
            status="SUCCESS",
            latency_ms=540
        )
        log3 = AgentRunLog(
            interaction_id=int3.id,
            tool_name="extract_structured_fields",
            input_payload={"raw_notes": "Avanex discussion, doctor worried about tiredness/fatigue, outcome query MSL"},
            output_payload={"discussion_topics": ["Avanex side effects profiling"], "products_discussed": ["Avanex"], "objections": "Expressed strong concerns about patient fatigue as a side effect."},
            status="SUCCESS",
            latency_ms=450
        )
        db.add_all([log1, log2, log3])

        db.commit()
        print("Database successfully seeded!")
        
        # Validation checks
        hcps_count = db.query(HCP).count()
        ints_count = db.query(Interaction).count()
        fus_count = db.query(FollowUp).count()
        logs_count = db.query(AgentRunLog).count()
        print(f"Validation: Found {hcps_count} HCPs, {ints_count} Interactions, {fus_count} Follow-ups, and {logs_count} Agent Run Logs in DB.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
