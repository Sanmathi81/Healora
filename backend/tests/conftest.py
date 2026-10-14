import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import UserRole
from app.models.doctor import DoctorProfile, DoctorAvailability
from app.models.patient import PatientProfile
from datetime import time

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_users(db_session):
    # Admin
    admin = User(
        email="admin@healora.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Hospital Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin)

    # Doctor
    doctor_user = User(
        email="doctor@healora.com",
        hashed_password=get_password_hash("DoctorPass123!"),
        full_name="Dr. Sarah Lin",
        role=UserRole.DOCTOR,
        is_active=True,
        is_verified=True
    )
    db_session.add(doctor_user)
    db_session.flush()

    doctor_prof = DoctorProfile(
        user_id=doctor_user.id,
        specialization="Cardiologist",
        license_number="MD-12345",
        department="Cardiology",
        years_of_experience=10,
        consultation_fee=120.0,
        is_approved=True
    )
    db_session.add(doctor_prof)
    db_session.flush()

    # Doctor availability (Monday=0 to Friday=4)
    for day in range(5):
        db_session.add(DoctorAvailability(
            doctor_id=doctor_prof.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration_minutes=30,
            is_available=True
        ))

    # Patient
    patient_user = User(
        email="patient@healora.com",
        hashed_password=get_password_hash("PatientPass123!"),
        full_name="John Doe",
        role=UserRole.PATIENT,
        is_active=True,
        is_verified=True
    )
    db_session.add(patient_user)
    db_session.flush()

    patient_prof = PatientProfile(
        user_id=patient_user.id,
        gender="Male",
        blood_group="O+"
    )
    db_session.add(patient_prof)
    db_session.commit()

    return {
        "admin": admin,
        "doctor_user": doctor_user,
        "doctor_profile": doctor_prof,
        "patient_user": patient_user,
        "patient_profile": patient_prof
    }
