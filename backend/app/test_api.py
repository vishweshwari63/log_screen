import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import SessionLocal
from app.models import Interaction, HCP

def run_api_tests():
    print("Initializing API Endpoint Integration Test...")
    client = TestClient(app)
    
    # Pre-condition: Check if database is populated (otherwise seed first)
    db = SessionLocal()
    hcp = db.query(HCP).first()
    db.close()
    if not hcp:
        print("Warning: Database appears empty. Please seed before testing.")

    # 1. Test GET /api/hcps?query=
    print("\n--- Testing GET /api/hcps?query=cardiology ---")
    response = client.get("/api/hcps?query=cardiology")
    print(f"Status: {response.status_code}")
    print(f"Content: {response.json().get('status', 'ERROR')}")
    print(f"Results Count: {len(response.json().get('results', []))}")
    assert response.status_code == 200

    # 2. Test POST /api/interactions/log
    print("\n--- Testing POST /api/interactions/log ---")
    log_payload = {
        "hcp_id": 1,
        "rep_id": "rep_999",
        "raw_text": "We had a detailed session discussing Crestor side effects. Dr John Doe was skeptical but agreed to try it.",
        "mode": "chat"
    }
    response = client.post("/api/interactions/log", json=log_payload)
    print(f"Status: {response.status_code}")
    json_data = response.json()
    print(f"Logged Status: {json_data.get('status')}")
    print(f"Summary: {json_data.get('summary')}")
    print(f"Trace size: {len(json_data.get('trace', []))}")
    assert response.status_code == 200
    interaction_id = json_data.get("interaction_id") or 1

    # 3. Test PATCH /api/interactions/{id}
    print(f"\n--- Testing PATCH /api/interactions/{interaction_id} ---")
    edit_payload = {
        "updates": {
            "outcome": "Rescheduled meeting for next month.",
            "sentiment": "NEUTRAL"
        }
    }
    response = client.patch(f"/api/interactions/{interaction_id}", json=edit_payload)
    print(f"Status: {response.status_code}")
    print(f"Updated fields: {response.json().get('updated_fields')}")
    assert response.status_code == 200

    # 4. Test POST /api/interactions/{id}/followup-email
    print(f"\n--- Testing POST /api/interactions/{interaction_id}/followup-email ---")
    response = client.post(f"/api/interactions/{interaction_id}/followup-email")
    print(f"Status: {response.status_code}")
    print(f"Email body exists: {'body' in response.json().get('email_body', '').lower()}")
    assert response.status_code == 200

    # 5. Test POST /api/interactions/{id}/compliance-check
    print(f"\n--- Testing POST /api/interactions/{interaction_id}/compliance-check ---")
    response = client.post(f"/api/interactions/{interaction_id}/compliance-check")
    print(f"Status: {response.status_code}")
    print(f"Compliance Severity: {response.json().get('severity')}")
    print(f"Flags: {response.json().get('risk_flags')}")
    assert response.status_code == 200

    # 6. Test GET /api/interactions/{id}/agent-trace
    print(f"\n--- Testing GET /api/interactions/{interaction_id}/agent-trace ---")
    response = client.get(f"/api/interactions/{interaction_id}/agent-trace")
    print(f"Status: {response.status_code}")
    print(f"Trace events logged in table: {len(response.json().get('trace', []))}")
    assert response.status_code == 200

    # 7. Test GET /api/interactions/stream (SSE streaming)
    print("\n--- Testing GET /api/interactions/stream (SSE) ---")
    url = "/api/interactions/stream?user_request=Find%20New%20York%20doctors&hcp_id=1&rep_id=rep_999"
    # To test streaming in TestClient, we use a context manager or client.send with stream=True
    # Here we stream the lines
    events_count = 0
    with client.stream("GET", url) as stream_resp:
        print(f"Streaming Status: {stream_resp.status_code}")
        assert stream_resp.status_code == 200
        for line in stream_resp.iter_lines():
            if line:
                events_count += 1
                if events_count <= 5: # print first few events
                    print(f"SSE line: {line[:120]} ...")
    print(f"Total SSE events streamed: {events_count}")
    assert events_count > 0
    
    print("\nAPI Integration Tests Passed Successfully!")

if __name__ == "__main__":
    run_api_tests()
