from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), unique=True, nullable=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis = Column(Text, nullable=False)
    clinical_notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    status = Column(String(50), default="COMPLETED", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    appointment = relationship("Appointment", back_populates="consultation")
    patient = relationship("PatientProfile", back_populates="consultations")
    doctor = relationship("DoctorProfile", back_populates="consultations")
    prescriptions = relationship("Prescription", back_populates="consultation", cascade="all, delete-orphan")
