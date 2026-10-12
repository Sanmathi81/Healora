from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.ai.agents import (
    AIClinicalSafetyGuard,
    DepartmentTriageAgent,
    QuerySummarizationAgent,
)
from app.core.config import settings
from app.core.dependencies import get_current_doctor, get_current_patient, get_current_user
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import NotificationType, QueryStatus, QueryUrgency, UserRole
from app.models.patient import PatientProfile
from app.models.query import DoctorResponse, PatientQuery
from app.models.user import User
from app.schemas.query import (
    DoctorResponseCreate,
    DoctorResponseResponse,
    PatientQueryCreate,
    PatientQueryResponse,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("", response_model=PatientQueryResponse, status_code=status.HTTP_201_CREATED)
def submit_patient_query(
    data: PatientQueryCreate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    # AI Triage & Classification
    urgency = data.urgency or AIClinicalSafetyGuard.evaluate_emergency(f"{data.title} {data.description}")
    department = data.department or DepartmentTriageAgent.classify_department(f"{data.title} {data.description}")
    ai_summary = QuerySummarizationAgent.summarize_query(data.title, data.description, urgency)

    # Determine assigned doctor if provided or auto-assign
    doctor_id = data.doctor_id
    if not doctor_id and settings.AUTO_ASSIGN_QUERIES:
        dept_doc = db.query(DoctorProfile).filter(
            DoctorProfile.department.ilike(f"%{department}%"),
            DoctorProfile.is_approved == True
        ).first()
        if dept_doc:
            doctor_id = dept_doc.id

    new_query = PatientQuery(
        patient_id=current_patient.id,
        doctor_id=doctor_id,
        department=department,
        title=data.title,
        description=data.description,
        urgency=urgency,
        status=QueryStatus.ASSIGNED if doctor_id else QueryStatus.SUBMITTED,
        ai_summary=ai_summary,
        is_ai_generated=True,
        triage_notes=f"Auto-classified department: {department}. Urgency level: {urgency.value}."
    )
    db.add(new_query)
    db.commit()
    db.refresh(new_query)

    # Notifications
    NotificationService.send_notification(
        db=db,
        user_id=current_patient.user_id,
        title="Query Submitted",
        message=f"Your query '{data.title}' has been submitted to the {department} department.",
        notification_type=NotificationType.QUERY_NEW,
        reference_id=str(new_query.id)
    )

    if doctor_id:
        doc = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
        if doc:
            NotificationService.send_notification(
                db=db,
                user_id=doc.user_id,
                title=f"New Patient Query ({urgency.value})",
                message=f"A new query '{data.title}' requires clinical attention.",
                notification_type=NotificationType.QUERY_ASSIGNED,
                reference_id=str(new_query.id)
            )

    AuditService.log(
        db=db,
        action="SUBMIT_PATIENT_QUERY",
        user_id=current_patient.user_id,
        entity_type="PatientQuery",
        entity_id=str(new_query.id),
        details=f"Query submitted in {department} with urgency {urgency.value}"
    )

    return new_query


@router.get("", response_model=List[PatientQueryResponse])
def list_queries(
    status_filter: Optional[QueryStatus] = Query(None, alias="status"),
    urgency_filter: Optional[QueryUrgency] = Query(None, alias="urgency"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PatientQuery)

    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not patient_profile:
            return []
        query = query.filter(PatientQuery.patient_id == patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not doctor_profile:
            return []
        # Doctor sees queries assigned to them OR queries unassigned in their department
        query = query.filter(
            (PatientQuery.doctor_id == doctor_profile.id) |
            ((PatientQuery.doctor_id == None) & (PatientQuery.department.ilike(f"%{doctor_profile.department}%")))
        )

    if status_filter:
        query = query.filter(PatientQuery.status == status_filter)
    if urgency_filter:
        query = query.filter(PatientQuery.urgency == urgency_filter)

    return query.order_by(PatientQuery.created_at.desc()).all()


@router.get("/{query_id}", response_model=PatientQueryResponse)
def get_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient_query = db.query(PatientQuery).filter(PatientQuery.id == query_id).first()
    if not patient_query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    if current_user.role == UserRole.PATIENT and patient_query.patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return patient_query


@router.post("/{query_id}/respond", response_model=DoctorResponseResponse, status_code=status.HTTP_201_CREATED)
def respond_to_query(
    query_id: int,
    data: DoctorResponseCreate,
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    patient_query = db.query(PatientQuery).filter(PatientQuery.id == query_id).first()
    if not patient_query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

    doctor_response = DoctorResponse(
        query_id=patient_query.id,
        doctor_id=current_doctor.id,
        response_text=data.response_text,
        recommendations=data.recommendations,
        is_clinical_advice=data.is_clinical_advice
    )
    db.add(doctor_response)

    # Update query status to RESOLVED and set assigned doctor
    patient_query.status = QueryStatus.RESOLVED
    patient_query.doctor_id = current_doctor.id

    db.commit()
    db.refresh(doctor_response)

    # Notify patient
    NotificationService.send_notification(
        db=db,
        user_id=patient_query.patient.user_id,
        title="Doctor Responded to Your Query",
        message=f"Dr. {current_doctor.user.full_name} has provided a clinical response to '{patient_query.title}'.",
        notification_type=NotificationType.QUERY_RESPONDED,
        reference_id=str(patient_query.id)
    )

    AuditService.log(
        db=db,
        action="DOCTOR_QUERY_RESPONSE",
        user_id=current_doctor.user_id,
        entity_type="PatientQuery",
        entity_id=str(patient_query.id),
        details=f"Doctor {current_doctor.id} responded to query {patient_query.id}"
    )

    return DoctorResponseResponse(
        id=doctor_response.id,
        query_id=doctor_response.query_id,
        doctor_id=doctor_response.doctor_id,
        doctor_name=current_doctor.user.full_name,
        response_text=doctor_response.response_text,
        recommendations=doctor_response.recommendations,
        is_clinical_advice=doctor_response.is_clinical_advice,
        created_at=doctor_response.created_at
    )
