from datetime import date, datetime, time, timedelta, timezone
from app.core.security import get_password_hash
from app.db.session import Base, SessionLocal, engine
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.doctor import DoctorAvailability, DoctorProfile
from app.models.enums import AppointmentStatus, NotificationType, QueryStatus, QueryUrgency, UserRole
from app.models.patient import PatientProfile
from app.models.query import DoctorResponse, PatientQuery
from app.models.record import MedicalRecord, Prescription
from app.models.user import User
from app.services.notification_service import NotificationService


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).filter(User.email == "admin@healora.com").first():
            print("Database already contains seed data.")
            return

        print("Seeding initial data...")

        # 1. Admin User
        admin_user = User(
            email="admin@healora.com",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="Hospital Administrator",
            phone_number="+1-555-0100",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)
        db.flush()

        # 2. Doctors
        doc1_user = User(
            email="dr.sarah@healora.com",
            hashed_password=get_password_hash("DoctorPass123!"),
            full_name="Dr. Sarah Lin",
            phone_number="+1-555-0101",
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True
        )
        db.add(doc1_user)
        db.flush()

        doc1_profile = DoctorProfile(
            user_id=doc1_user.id,
            specialization="Cardiologist",
            license_number="MD-CAR-98214",
            department="Cardiology",
            years_of_experience=12,
            bio="Senior Interventional Cardiologist specializing in cardiovascular wellness and preventative heart care.",
            consultation_fee=150.0,
            is_approved=True
        )
        db.add(doc1_profile)
        db.flush()

        # Add doctor 1 availability (Monday to Friday, 9:00 to 17:00, 30 min slots)
        for day in range(5):
            db.add(DoctorAvailability(
                doctor_id=doc1_profile.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                slot_duration_minutes=30,
                is_available=True
            ))

        doc2_user = User(
            email="dr.rajesh@healora.com",
            hashed_password=get_password_hash("DoctorPass123!"),
            full_name="Dr. Rajesh Mehta",
            phone_number="+1-555-0102",
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True
        )
        db.add(doc2_user)
        db.flush()

        doc2_profile = DoctorProfile(
            user_id=doc2_user.id,
            specialization="Orthopedic Surgeon",
            license_number="MD-ORT-54312",
            department="Orthopedics",
            years_of_experience=9,
            bio="Orthopedic specialist focusing on sports injuries, joint preservation, and rehabilitation.",
            consultation_fee=130.0,
            is_approved=True
        )
        db.add(doc2_profile)
        db.flush()

        # 3. Patient
        patient_user = User(
            email="patient@healora.com",
            hashed_password=get_password_hash("PatientPass123!"),
            full_name="John Doe",
            phone_number="+1-555-0199",
            role=UserRole.PATIENT,
            is_active=True,
            is_verified=True
        )
        db.add(patient_user)
        db.flush()

        patient_profile = PatientProfile(
            user_id=patient_user.id,
            date_of_birth=date(1990, 5, 14),
            gender="Male",
            blood_group="O+",
            emergency_contact="+1-555-9911",
            address="124 Park Avenue, Metropolis",
            allergies="Penicillin",
            medical_history_summary="Mild seasonal asthma, non-smoker, active runner."
        )
        db.add(patient_profile)
        db.flush()

        # 4. Sample Appointment
        appt_date = date.today() + timedelta(days=2)
        appointment = Appointment(
            patient_id=patient_profile.id,
            doctor_id=doc1_profile.id,
            appointment_date=appt_date,
            start_time=time(10, 0),
            end_time=time(10, 30),
            status=AppointmentStatus.CONFIRMED,
            reason="Annual cardiovascular review and resting ECG evaluation.",
            notes="Patient requested morning appointment."
        )
        db.add(appointment)
        db.flush()

        # 5. Sample Query & Doctor Response
        query = PatientQuery(
            patient_id=patient_profile.id,
            doctor_id=doc1_profile.id,
            department="Cardiology",
            title="Mild chest tightness after high-altitude jogging",
            description="Felt a brief heaviness in the sternal area yesterday after running 5 miles in chilly weather. Resolved after 5 minutes of rest.",
            urgency=QueryUrgency.MEDIUM,
            status=QueryStatus.RESOLVED,
            ai_summary="**Chief Complaint:** Mild chest tightness\n**Urgency:** MEDIUM\n**Reported Symptoms:** Exertional chest tightness in cold weather, resolved with rest.\n**AI Triage:** Clinical evaluation recommended.",
            is_ai_generated=True,
            triage_notes="Auto-classified into Cardiology. Urgency: MEDIUM."
        )
        db.add(query)
        db.flush()

        response = DoctorResponse(
            query_id=query.id,
            doctor_id=doc1_profile.id,
            response_text="Hello John, thank you for checking in. Given your symptoms, it is important to avoid cold air vigorous runs until we review your resting and exercise ECG in our upcoming appointment. If you experience shortness of breath, radiating pain to the arm or jaw, or chest pressure lasting >5 minutes, please visit an emergency department immediately.",
            recommendations="Rest from intense cardio; keep a blood pressure log.",
            is_clinical_advice=True
        )
        db.add(response)

        # 6. Sample Prescription
        prescription = Prescription(
            patient_id=patient_profile.id,
            doctor_id=doc1_profile.id,
            diagnosis="Exercise-induced bronchial reactivity vs mild vasospasm",
            medications=[
                {
                    "name": "Albuterol Inhaler",
                    "dosage": "90mcg",
                    "frequency": "2 puffs 15 minutes before exertion",
                    "duration": "As needed",
                    "instructions": "Rinse mouth after inhalation"
                }
            ],
            notes="Follow up at upcoming in-person appointment."
        )
        db.add(prescription)

        # 7. Notifications
        NotificationService.send_notification(
            db=db,
            user_id=patient_user.id,
            title="Appointment Confirmed",
            message=f"Your appointment with Dr. Sarah Lin on {appt_date} at 10:00 AM has been confirmed.",
            notification_type=NotificationType.APPOINTMENT_BOOKED,
            reference_id=str(appointment.id)
        )

        db.commit()
        print("Initial database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
