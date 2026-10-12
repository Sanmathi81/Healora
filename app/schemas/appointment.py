from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import AppointmentStatus
from app.schemas.doctor import DoctorProfileResponse
from app.schemas.patient import PatientProfileResponse


class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: date
    start_time: time
    reason: str
    notes: Optional[str] = None


class AppointmentReschedule(BaseModel):
    appointment_date: date
    start_time: time
    reason: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    reason: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientProfileResponse] = None
    doctor: Optional[DoctorProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AvailableSlot(BaseModel):
    date: date
    start_time: time
    end_time: time
    is_available: bool
