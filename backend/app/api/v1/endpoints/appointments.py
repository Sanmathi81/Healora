from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.ai.agents import AppointmentAgent
from app.core.config import settings
from app.core.dependencies import get_current_patient, get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import DoctorAvailability, DoctorProfile
from app.models.enums import AppointmentStatus, NotificationType, UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentStatusUpdate,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: AppointmentCreate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    # Verify doctor exists and is approved
    doctor = db.query(DoctorProfile).filter(
        DoctorProfile.id == data.doctor_id,
        DoctorProfile.is_approved == True
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or not currently active"
        )

    # Determine slot duration
    day_of_week = data.appointment_date.weekday()
    avail = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.day_of_week == day_of_week
    ).first()
    duration_min = avail.slot_duration_minutes if avail else settings.DEFAULT_APPOINTMENT_DURATION_MINUTES

    start_dt = datetime.combine(data.appointment_date, data.start_time)
    end_dt = start_dt + timedelta(minutes=duration_min)
    end_time = end_dt.time()

    # Check for scheduling conflicts
    existing_appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == data.appointment_date
    ).all()

    if AppointmentAgent.check_conflicts(existing_appts, data.start_time, end_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested appointment time slot is already booked. Please select another slot."
        )

    new_appointment = Appointment(
        patient_id=current_patient.id,
        doctor_id=doctor.id,
        appointment_date=data.appointment_date,
        start_time=data.start_time,
        end_time=end_time,
        status=AppointmentStatus.PENDING,
        reason=data.reason,
        notes=data.notes
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    # Send notifications
    NotificationService.send_notification(
        db=db,
        user_id=current_patient.user_id,
        title="Appointment Booked",
        message=f"Your appointment with Dr. {doctor.user.full_name} on {data.appointment_date} at {data.start_time.strftime('%H:%M')} has been requested.",
        notification_type=NotificationType.APPOINTMENT_BOOKED,
        reference_id=str(new_appointment.id)
    )
    NotificationService.send_notification(
        db=db,
        user_id=doctor.user_id,
        title="New Appointment Request",
        message=f"Patient {current_patient.user.full_name} requested an appointment on {data.appointment_date} at {data.start_time.strftime('%H:%M')}.",
        notification_type=NotificationType.APPOINTMENT_BOOKED,
        reference_id=str(new_appointment.id)
    )

    # Audit log
    AuditService.log(
        db=db,
        action="BOOK_APPOINTMENT",
        user_id=current_patient.user_id,
        entity_type="Appointment",
        entity_id=str(new_appointment.id),
        details=f"Booked with Doctor ID {doctor.id} on {data.appointment_date}"
    )

    return new_appointment


@router.get("", response_model=List[AppointmentResponse])
def list_appointments(
    status_filter: Optional[AppointmentStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)

    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if not patient_profile:
            return []
        query = query.filter(Appointment.patient_id == patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if not doctor_profile:
            return []
        query = query.filter(Appointment.doctor_id == doctor_profile.id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    return query.order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Authorize access
    if current_user.role == UserRole.PATIENT and appt.patient.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.DOCTOR and appt.doctor.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return appt


@router.put("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Check permission
    is_patient = (current_user.role == UserRole.PATIENT and appt.patient.user_id == current_user.id)
    is_doctor = (current_user.role == UserRole.DOCTOR and appt.doctor.user_id == current_user.id)
    is_admin = (current_user.role == UserRole.ADMIN)

    if not (is_patient or is_doctor or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Calculate new end time
    day_of_week = data.appointment_date.weekday()
    avail = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == appt.doctor_id,
        DoctorAvailability.day_of_week == day_of_week
    ).first()
    duration_min = avail.slot_duration_minutes if avail else settings.DEFAULT_APPOINTMENT_DURATION_MINUTES

    start_dt = datetime.combine(data.appointment_date, data.start_time)
    end_dt = start_dt + timedelta(minutes=duration_min)
    end_time = end_dt.time()

    # Check conflicts excluding self
    existing_appts = db.query(Appointment).filter(
        Appointment.doctor_id == appt.doctor_id,
        Appointment.appointment_date == data.appointment_date,
        Appointment.id != appt.id
    ).all()

    if AppointmentAgent.check_conflicts(existing_appts, data.start_time, end_time):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target slot is already booked")

    appt.appointment_date = data.appointment_date
    appt.start_time = data.start_time
    appt.end_time = end_time
    appt.status = AppointmentStatus.RESCHEDULED
    if data.reason:
        appt.notes = f"{appt.notes or ''}\nRescheduled: {data.reason}".strip()

    db.commit()
    db.refresh(appt)

    # Notifications
    notify_user_id = appt.doctor.user_id if is_patient else appt.patient.user_id
    NotificationService.send_notification(
        db=db,
        user_id=notify_user_id,
        title="Appointment Rescheduled",
        message=f"Appointment #{appt.id} rescheduled to {appt.appointment_date} at {appt.start_time.strftime('%H:%M')}",
        notification_type=NotificationType.APPOINTMENT_RESCHEDULED,
        reference_id=str(appt.id)
    )

    return appt


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: int,
    data: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Patients can only CANCEL
    if current_user.role == UserRole.PATIENT:
        if appt.patient.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if data.status != AppointmentStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patients can only cancel appointments")

    # Doctors can confirm, complete, or cancel
    if current_user.role == UserRole.DOCTOR:
        if appt.doctor.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    appt.status = data.status
    if data.notes:
        appt.notes = f"{appt.notes or ''}\n{data.notes}".strip()

    db.commit()
    db.refresh(appt)

    # Notify counterpart
    target_user_id = appt.patient.user_id if current_user.id != appt.patient.user_id else appt.doctor.user_id
    notif_type = NotificationType.APPOINTMENT_CANCELLED if data.status == AppointmentStatus.CANCELLED else NotificationType.APPOINTMENT_REMINDER
    NotificationService.send_notification(
        db=db,
        user_id=target_user_id,
        title=f"Appointment {data.status.value.title()}",
        message=f"Appointment #{appt.id} status changed to {data.status.value}",
        notification_type=notif_type,
        reference_id=str(appt.id)
    )

    return appt
