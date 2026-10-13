from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import QueryStatus, QueryUrgency


class PatientQuery(Base):
    __tablename__ = "patient_queries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    urgency = Column(Enum(QueryUrgency), default=QueryUrgency.MEDIUM, nullable=False)
    status = Column(Enum(QueryStatus), default=QueryStatus.SUBMITTED, nullable=False, index=True)
    ai_summary = Column(Text, nullable=True)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    triage_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    patient = relationship("PatientProfile", back_populates="queries")
    doctor = relationship("DoctorProfile", back_populates="assigned_queries")
    responses = relationship("DoctorResponse", back_populates="query", cascade="all, delete-orphan")


class DoctorResponse(Base):
    __tablename__ = "doctor_responses"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("patient_queries.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    response_text = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=True)
    is_clinical_advice = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    query = relationship("PatientQuery", back_populates="responses")
    doctor = relationship("DoctorProfile", back_populates="responses")
