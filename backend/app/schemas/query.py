from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import QueryStatus, QueryUrgency


class DoctorResponseCreate(BaseModel):
    response_text: str
    recommendations: Optional[str] = None
    is_clinical_advice: bool = True


class DoctorResponseResponse(BaseModel):
    id: int
    query_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    response_text: str
    recommendations: Optional[str] = None
    is_clinical_advice: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientQueryCreate(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    doctor_id: Optional[int] = None
    urgency: Optional[QueryUrgency] = None


class PatientQueryResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    department: Optional[str] = None
    title: str
    description: str
    urgency: QueryUrgency
    status: QueryStatus
    ai_summary: Optional[str] = None
    is_ai_generated: bool
    triage_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    responses: List[DoctorResponseResponse] = []

    model_config = ConfigDict(from_attributes=True)
