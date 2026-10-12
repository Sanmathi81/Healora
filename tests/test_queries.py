from fastapi import status


def get_token(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def test_submit_query_and_doctor_response(client, seeded_users):
    patient_token = get_token(client, "patient@healora.com", "PatientPass123!")
    doctor_token = get_token(client, "doctor@healora.com", "DoctorPass123!")

    # 1. Patient submits query with emergency symptoms
    query_resp = client.post(
        "/api/v1/queries",
        json={
            "title": "Severe shortness of breath",
            "description": "I suddenly can barely catch my breath and chest feels very tight."
        },
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert query_resp.status_code == status.HTTP_201_CREATED
    query_data = query_resp.json()
    assert query_data["urgency"] == "EMERGENCY"
    assert "NOTICE: This automated assessment is for informational and triage purposes only." in query_data["ai_summary"]
    query_id = query_data["id"]

    # 2. Doctor responds to query
    resp_payload = {
        "response_text": "Please go to the nearest emergency room or call emergency services immediately.",
        "recommendations": "Do not exert yourself. Sit upright.",
        "is_clinical_advice": True
    }
    doc_resp = client.post(
        f"/api/v1/queries/{query_id}/respond",
        json=resp_payload,
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert doc_resp.status_code == status.HTTP_201_CREATED
    doc_data = doc_resp.json()
    assert doc_data["response_text"] == resp_payload["response_text"]
