from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_doctor, get_current_user
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import NotificationType, UserRole
from app.models.patient import PatientProfile
from app.models.record import Prescription
from app.models.user import User
from app.schemas.record import PrescriptionCreate, PrescriptionResponse
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def issue_prescription(
    data: PrescriptionCreate,
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    patient = db.query(PatientProfile).filter(PatientProfile.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    meds_dict_list = [med.model_dump() for med in data.medications]

    prescription = Prescription(
        patient_id=data.patient_id,
        doctor_id=current_doctor.id,
        consultation_id=data.consultation_id,
        diagnosis=data.diagnosis,
        medications=meds_dict_list,
        notes=data.notes
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    # Notify patient
    NotificationService.send_notification(
        db=db,
        user_id=patient.user_id,
        title="Prescription Issued",
        message=f"Dr. {current_doctor.user.full_name} has issued a new prescription for {data.diagnosis}.",
        notification_type=NotificationType.PRESCRIPTION_ISSUED,
        reference_id=str(prescription.id)
    )

    AuditService.log(
        db=db,
        action="ISSUE_PRESCRIPTION",
        user_id=current_doctor.user_id,
        entity_type="Prescription",
        entity_id=str(prescription.id),
        details=f"Prescription issued with {len(meds_dict_list)} medications"
    )

    return PrescriptionResponse(
        id=prescription.id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        consultation_id=prescription.consultation_id,
        diagnosis=prescription.diagnosis,
        medications=prescription.medications,
        notes=prescription.notes,
        issued_at=prescription.issued_at,
        doctor_name=current_doctor.user.full_name,
        patient_name=patient.user.full_name
    )


@router.get("", response_model=List[PrescriptionResponse])
def list_prescriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Prescription)
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not patient_profile:
            return []
        query = query.filter(Prescription.patient_id == patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not doctor_profile:
            return []
        query = query.filter(Prescription.doctor_id == doctor_profile.id)

    prescriptions = query.order_by(Prescription.issued_at.desc()).all()
    results = []
    for p in prescriptions:
        results.append(
            PrescriptionResponse(
                id=p.id,
                patient_id=p.patient_id,
                doctor_id=p.doctor_id,
                consultation_id=p.consultation_id,
                diagnosis=p.diagnosis,
                medications=p.medications,
                notes=p.notes,
                issued_at=p.issued_at,
                doctor_name=p.doctor.user.full_name if p.doctor and p.doctor.user else None,
                patient_name=p.patient.user.full_name if p.patient and p.patient.user else None
            )
        )
    return results


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")

    if current_user.role == UserRole.PATIENT and p.patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return PrescriptionResponse(
        id=p.id,
        patient_id=p.patient_id,
        doctor_id=p.doctor_id,
        consultation_id=p.consultation_id,
        diagnosis=p.diagnosis,
        medications=p.medications,
        notes=p.notes,
        issued_at=p.issued_at,
        doctor_name=p.doctor.user.full_name if p.doctor and p.doctor.user else None,
        patient_name=p.patient.user.full_name if p.patient and p.patient.user else None
    )
