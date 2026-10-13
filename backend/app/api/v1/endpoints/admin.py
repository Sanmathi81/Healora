from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_admin
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.audit import AuditLog
from app.models.consultation import Consultation
from app.models.doctor import DoctorProfile
from app.models.enums import NotificationType, UserRole
from app.models.patient import PatientProfile
from app.models.query import PatientQuery
from app.models.user import User
from app.schemas.doctor import DoctorProfileResponse, DoctorVerifyRequest
from app.schemas.user import UserResponse, UserStatusUpdate
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.order_by(User.id.desc()).all()


@router.put("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_verified is not None:
        user.is_verified = data.is_verified

    db.commit()
    db.refresh(user)

    AuditService.log(
        db=db,
        action="UPDATE_USER_STATUS",
        user_id=current_admin.id,
        entity_type="User",
        entity_id=str(user.id),
        details=f"Admin updated active={user.is_active}, verified={user.is_verified}"
    )

    return user


@router.get("/doctors/pending", response_model=List[DoctorProfileResponse])
def list_pending_doctors(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(DoctorProfile).filter(DoctorProfile.is_approved == False).all()


@router.put("/doctors/{doctor_id}/verify", response_model=DoctorProfileResponse)
def verify_doctor(
    doctor_id: int,
    data: DoctorVerifyRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    doctor.is_approved = data.is_approved
    if data.is_approved:
        doctor.user.is_verified = True

    db.commit()
    db.refresh(doctor)

    status_str = "Approved" if data.is_approved else "Rejected"
    NotificationService.send_notification(
        db=db,
        user_id=doctor.user_id,
        title=f"Doctor Verification {status_str}",
        message=f"Your doctor profile application has been {status_str.lower()} by the administration.",
        notification_type=NotificationType.ACCOUNT_STATUS,
        reference_id=str(doctor.id)
    )

    AuditService.log(
        db=db,
        action="VERIFY_DOCTOR",
        user_id=current_admin.id,
        entity_type="DoctorProfile",
        entity_id=str(doctor.id),
        details=f"Admin set approval to {data.is_approved}"
    )

    return doctor


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, le=200),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs


@router.get("/stats")
def get_platform_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    total_users = db.query(User).count()
    total_patients = db.query(PatientProfile).count()
    total_doctors = db.query(DoctorProfile).count()
    approved_doctors = db.query(DoctorProfile).filter(DoctorProfile.is_approved == True).count()
    pending_doctors = db.query(DoctorProfile).filter(DoctorProfile.is_approved == False).count()
    total_appointments = db.query(Appointment).count()
    total_queries = db.query(PatientQuery).count()
    total_consultations = db.query(Consultation).count()

    return {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "approved_doctors": approved_doctors,
        "pending_doctors": pending_doctors,
        "total_appointments": total_appointments,
        "total_queries": total_queries,
        "total_consultations": total_consultations,
    }
