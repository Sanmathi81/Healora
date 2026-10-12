from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class DoctorAvailabilityBase(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30
    is_available: bool = True


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass


class DoctorAvailabilityResponse(DoctorAvailabilityBase):
    id: int
    doctor_id: int

    model_config = ConfigDict(from_attributes=True)


class DoctorProfileBase(BaseModel):
    specialization: str
    license_number: str
    department: str
    years_of_experience: int = 0
    bio: Optional[str] = None
    consultation_fee: float = 0.0


class DoctorProfileUpdate(BaseModel):
    specialization: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = None
    bio: Optional[str] = None
    consultation_fee: Optional[float] = None


class DoctorProfileResponse(DoctorProfileBase):
    id: int
    user_id: int
    is_approved: bool
    user: Optional[UserResponse] = None
    availability_slots: List[DoctorAvailabilityResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorAvailabilityBatchUpdate(BaseModel):
    slots: List[DoctorAvailabilityCreate]


class DoctorVerifyRequest(BaseModel):
    is_approved: bool = True
