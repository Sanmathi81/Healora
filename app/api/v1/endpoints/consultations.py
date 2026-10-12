from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_doctor, get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.doctor import DoctorProfile
from app.models.enums import AppointmentStatus, UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationResponse,
    ConsultationUpdate,
)
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    data: ConsultationCreate,
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    # Verify patient exists
    patient = db.query(PatientProfile).filter(PatientProfile.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    # If appointment linked, verify and mark completed
    if data.appointment_id:
        appt = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
        if appt:
            appt.status = AppointmentStatus.COMPLETED

    consultation = Consultation(
        appointment_id=data.appointment_id,
        patient_id=data.patient_id,
        doctor_id=current_doctor.id,
        diagnosis=data.diagnosis,
        clinical_notes=data.clinical_notes,
        follow_up_date=data.follow_up_date,
        status=data.status
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    AuditService.log(
        db=db,
        action="CREATE_CONSULTATION",
        user_id=current_doctor.user_id,
        entity_type="Consultation",
        entity_id=str(consultation.id),
        details=f"Doctor {current_doctor.id} created consultation for patient {patient.id}"
    )

    return ConsultationResponse(
        id=consultation.id,
        appointment_id=consultation.appointment_id,
        patient_id=consultation.patient_id,
        doctor_id=consultation.doctor_id,
        diagnosis=consultation.diagnosis,
        clinical_notes=consultation.clinical_notes,
        follow_up_date=consultation.follow_up_date,
        status=consultation.status,
        created_at=consultation.created_at,
        doctor_name=current_doctor.user.full_name,
        patient_name=patient.user.full_name
    )


@router.get("", response_model=List[ConsultationResponse])
def list_consultations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Consultation)
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not patient_profile:
            return []
        query = query.filter(Consultation.patient_id == patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not doctor_profile:
            return []
        query = query.filter(Consultation.doctor_id == doctor_profile.id)

    consultations = query.order_by(Consultation.created_at.desc()).all()
    results = []
    for c in consultations:
        results.append(
            ConsultationResponse(
                id=c.id,
                appointment_id=c.appointment_id,
                patient_id=c.patient_id,
                doctor_id=c.doctor_id,
                diagnosis=c.diagnosis,
                clinical_notes=c.clinical_notes,
                follow_up_date=c.follow_up_date,
                status=c.status,
                created_at=c.created_at,
                doctor_name=c.doctor.user.full_name if c.doctor and c.doctor.user else None,
                patient_name=c.patient.user.full_name if c.patient and c.patient.user else None
            )
        )
    return results


@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")

    if current_user.role == UserRole.PATIENT and c.patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return ConsultationResponse(
        id=c.id,
        appointment_id=c.appointment_id,
        patient_id=c.patient_id,
        doctor_id=c.doctor_id,
        diagnosis=c.diagnosis,
        clinical_notes=c.clinical_notes,
        follow_up_date=c.follow_up_date,
        status=c.status,
        created_at=c.created_at,
        doctor_name=c.doctor.user.full_name if c.doctor and c.doctor.user else None,
        patient_name=c.patient.user.full_name if c.patient and c.patient.user else None
    )
