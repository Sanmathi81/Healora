from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class PatientProfileBase(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None
    medical_history_summary: Optional[str] = None


class PatientProfileUpdate(PatientProfileBase):
    pass


class PatientProfileResponse(PatientProfileBase):
    id: int
    user_id: int
    user: Optional[UserResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
