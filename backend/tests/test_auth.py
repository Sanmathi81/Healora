from fastapi import status


def test_login_success(client, seeded_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@healora.com", "password": "PatientPass123!"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "PATIENT"
    assert data["email"] == "patient@healora.com"


def test_login_invalid_password(client, seeded_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@healora.com", "password": "WrongPassword123"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_register_new_patient(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new.patient@test.com",
            "password": "SecurePassword123!",
            "full_name": "Alice Wonderland",
            "role": "PATIENT"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "new.patient@test.com"
    assert data["role"] == "PATIENT"


def test_get_current_user_me(client, seeded_users):
    # Log in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "doctor@healora.com", "password": "DoctorPass123!"}
    )
    token = login_resp.json()["access_token"]

    # Call /me
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == status.HTTP_200_OK
    user = me_resp.json()
    assert user["email"] == "doctor@healora.com"
    assert user["role"] == "DOCTOR"
