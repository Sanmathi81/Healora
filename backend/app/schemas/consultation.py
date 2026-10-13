from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ConsultationCreate(BaseModel):
    appointment_id: Optional[int] = None
    patient_id: int
    diagnosis: str
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    status: str = "COMPLETED"


class ConsultationUpdate(BaseModel):
    diagnosis: Optional[str] = None
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    status: Optional[str] = None


class ConsultationResponse(BaseModel):
    id: int
    appointment_id: Optional[int] = None
    patient_id: int
    doctor_id: int
    diagnosis: str
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    status: str
    created_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
