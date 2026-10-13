from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class MedicationItem(BaseModel):
    name: str
    dosage: str  # e.g., "500mg"
    frequency: str  # e.g., "Twice daily after meals"
    duration: str  # e.g., "5 days"
    instructions: Optional[str] = None


class PrescriptionCreate(BaseModel):
    patient_id: int
    consultation_id: Optional[int] = None
    diagnosis: str
    medications: List[MedicationItem]
    notes: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    consultation_id: Optional[int] = None
    diagnosis: str
    medications: List[Dict[str, Any]]
    notes: Optional[str] = None
    issued_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MedicalRecordCreate(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    record_type: str  # e.g., LAB_REPORT, DISCHARGE_SUMMARY, IMAGING, CLINICAL_NOTE
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    record_type: str
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
