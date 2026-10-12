from datetime import date, datetime, timedelta, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_doctor, get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import DoctorAvailability, DoctorProfile
from app.models.enums import AppointmentStatus
from app.models.user import User
from app.schemas.appointment import AvailableSlot
from app.schemas.doctor import (
    DoctorAvailabilityBatchUpdate,
    DoctorAvailabilityResponse,
    DoctorProfileResponse,
    DoctorProfileUpdate,
)
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=List[DoctorProfileResponse])
def list_doctors(
    department: Optional[str] = None,
    specialization: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(DoctorProfile).filter(DoctorProfile.is_approved == True)

    if department:
        query = query.filter(DoctorProfile.department.ilike(f"%{department}%"))
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    if search:
        query = query.join(User).filter(
            (User.full_name.ilike(f"%{search}%")) |
            (DoctorProfile.specialization.ilike(f"%{search}%")) |
            (DoctorProfile.department.ilike(f"%{search}%"))
        )

    return query.all()


@router.get("/profile/me", response_model=DoctorProfileResponse)
def get_my_doctor_profile(
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    return current_doctor


@router.put("/profile/me", response_model=DoctorProfileResponse)
def update_my_doctor_profile(
    update_data: DoctorProfileUpdate,
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current_doctor, key, value)

    db.commit()
    db.refresh(current_doctor)

    AuditService.log(
        db=db,
        action="UPDATE_DOCTOR_PROFILE",
        user_id=current_doctor.user_id,
        entity_type="DoctorProfile",
        entity_id=str(current_doctor.id),
        details="Doctor updated profile"
    )

    return current_doctor


@router.get("/{doctor_id}", response_model=DoctorProfileResponse)
def get_doctor_profile_by_id(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    return doctor


@router.post("/availability", response_model=List[DoctorAvailabilityResponse])
def set_doctor_availability(
    batch_data: DoctorAvailabilityBatchUpdate,
    current_doctor: DoctorProfile = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    # Clear existing availability
    db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == current_doctor.id).delete()

    created_slots = []
    for slot in batch_data.slots:
        new_slot = DoctorAvailability(
            doctor_id=current_doctor.id,
            day_of_week=slot.day_of_week,
            start_time=slot.start_time,
            end_time=slot.end_time,
            slot_duration_minutes=slot.slot_duration_minutes,
            is_available=slot.is_available
        )
        db.add(new_slot)
        created_slots.append(new_slot)

    db.commit()
    for s in created_slots:
        db.refresh(s)

    AuditService.log(
        db=db,
        action="SET_DOCTOR_AVAILABILITY",
        user_id=current_doctor.user_id,
        entity_type="DoctorProfile",
        entity_id=str(current_doctor.id),
        details=f"Configured {len(created_slots)} availability recurring slots"
    )

    return created_slots


@router.get("/{doctor_id}/slots", response_model=List[AvailableSlot])
def get_doctor_available_slots_for_date(
    doctor_id: int,
    target_date: date = Query(..., description="Target date to check availability (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Day of week in Python: 0=Monday, 6=Sunday
    day_of_week = target_date.weekday()

    availabilities = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == day_of_week,
        DoctorAvailability.is_available == True
    ).all()

    # Get booked appointments on target date
    booked_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED])
    ).all()

    booked_ranges = [(appt.start_time, appt.end_time) for appt in booked_appointments]

    slots: List[AvailableSlot] = []

    for av in availabilities:
        current_dt = datetime.combine(target_date, av.start_time)
        end_dt = datetime.combine(target_date, av.end_time)
        duration = timedelta(minutes=av.slot_duration_minutes)

        while current_dt + duration <= end_dt:
            slot_start = current_dt.time()
            slot_end = (current_dt + duration).time()

            # Check if this slot conflicts with booked appointments
            is_booked = any(
                (slot_start < b_end and slot_end > b_start)
                for b_start, b_end in booked_ranges
            )

            slots.append(
                AvailableSlot(
                    date=target_date,
                    start_time=slot_start,
                    end_time=slot_end,
                    is_available=not is_booked
                )
            )
            current_dt += duration

    return slots
