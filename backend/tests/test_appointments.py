from datetime import date, timedelta, time
from fastapi import status


def get_token(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def test_book_appointment_and_conflict(client, seeded_users):
    patient_token = get_token(client, "patient@healora.com", "PatientPass123!")
    doctor_id = seeded_users["doctor_profile"].id

    # Book next Monday
    appt_date = (date.today() + timedelta(days=(7 - date.today().weekday()) % 7)).isoformat()

    # 1. Successful booking
    book_resp = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": appt_date,
            "start_time": "10:00:00",
            "reason": "Chest tightness consultation"
        },
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert book_resp.status_code == status.HTTP_201_CREATED
    data = book_resp.json()
    assert data["reason"] == "Chest tightness consultation"
    assert data["doctor_id"] == doctor_id

    # 2. Duplicate / conflicting booking attempt
    conflict_resp = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": doctor_id,
            "appointment_date": appt_date,
            "start_time": "10:00:00",
            "reason": "Another checkup in same slot"
        },
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert conflict_resp.status_code == status.HTTP_409_CONFLICT
