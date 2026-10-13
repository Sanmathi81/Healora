import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.dependencies import get_current_patient, get_current_user
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import NotificationType, UserRole
from app.models.patient import PatientProfile
from app.models.record import MedicalRecord
from app.models.user import User
from app.schemas.record import MedicalRecordCreate, MedicalRecordResponse
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_medical_record(
    data: MedicalRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(PatientProfile).filter(PatientProfile.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    doctor_id = data.doctor_id
    if current_user.role == UserRole.DOCTOR:
        doc = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if doc:
            doctor_id = doc.id

    record = MedicalRecord(
        patient_id=data.patient_id,
        doctor_id=doctor_id,
        record_type=data.record_type,
        title=data.title,
        description=data.description,
        file_url=data.file_url
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    NotificationService.send_notification(
        db=db,
        user_id=patient.user_id,
        title="Medical Record Added",
        message=f"A new record '{data.title}' ({data.record_type}) was added to your profile.",
        notification_type=NotificationType.MEDICAL_RECORD_ADDED,
        reference_id=str(record.id)
    )

    AuditService.log(
        db=db,
        action="ADD_MEDICAL_RECORD",
        user_id=current_user.id,
        entity_type="MedicalRecord",
        entity_id=str(record.id),
        details=f"Record added: {data.title}"
    )

    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        doctor_id=record.doctor_id,
        record_type=record.record_type,
        title=record.title,
        description=record.description,
        file_url=record.file_url,
        created_at=record.created_at,
        patient_name=patient.user.full_name
    )


@router.post("/upload", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def upload_medical_record_file(
    title: str = Form(...),
    record_type: str = Form(...),
    description: Optional[str] = Form(None),
    patient_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Determine target patient
    target_patient_id = patient_id
    if current_user.role == UserRole.PATIENT:
        p = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
        target_patient_id = p.id

    if not target_patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required")

    patient = db.query(PatientProfile).filter(PatientProfile.id == target_patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    doctor_id = None
    if current_user.role == UserRole.DOCTOR:
        doc = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if doc:
            doctor_id = doc.id

    record = MedicalRecord(
        patient_id=target_patient_id,
        doctor_id=doctor_id,
        record_type=record_type,
        title=title,
        description=description,
        file_url=f"/uploads/{filename}"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    AuditService.log(
        db=db,
        action="UPLOAD_MEDICAL_RECORD_FILE",
        user_id=current_user.id,
        entity_type="MedicalRecord",
        entity_id=str(record.id),
        details=f"Uploaded file for {title}"
    )

    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        doctor_id=record.doctor_id,
        record_type=record.record_type,
        title=record.title,
        description=record.description,
        file_url=record.file_url,
        created_at=record.created_at,
        patient_name=patient.user.full_name
    )


@router.get("", response_model=List[MedicalRecordResponse])
def list_medical_records(
    patient_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(MedicalRecord)

    if current_user.role == UserRole.PATIENT:
        p = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not p:
            return []
        query = query.filter(MedicalRecord.patient_id == p.id)
    elif current_user.role in [UserRole.DOCTOR, UserRole.ADMIN] and patient_id:
        query = query.filter(MedicalRecord.patient_id == patient_id)

    records = query.order_by(MedicalRecord.created_at.desc()).all()
    results = []
    for r in records:
        results.append(
            MedicalRecordResponse(
                id=r.id,
                patient_id=r.patient_id,
                doctor_id=r.doctor_id,
                record_type=r.record_type,
                title=r.title,
                description=r.description,
                file_url=r.file_url,
                created_at=r.created_at,
                doctor_name=r.doctor.user.full_name if r.doctor and r.doctor.user else None,
                patient_name=r.patient.user.full_name if r.patient and r.patient.user else None
            )
        )
    return results


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")

    if current_user.role == UserRole.PATIENT and r.patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return MedicalRecordResponse(
        id=r.id,
        patient_id=r.patient_id,
        doctor_id=r.doctor_id,
        record_type=r.record_type,
        title=r.title,
        description=r.description,
        file_url=r.file_url,
        created_at=r.created_at,
        doctor_name=r.doctor.user.full_name if r.doctor and r.doctor.user else None,
        patient_name=r.patient.user.full_name if r.patient and r.patient.user else None
    )
