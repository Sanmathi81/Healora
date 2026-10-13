from app.schemas.auth import LoginRequest, RegisterRequest, RefreshTokenRequest, TokenResponse, TokenPayload
from app.schemas.user import UserResponse, UserStatusUpdate
from app.schemas.patient import PatientProfileBase, PatientProfileUpdate, PatientProfileResponse
from app.schemas.doctor import (
    DoctorAvailabilityBase,
    DoctorAvailabilityCreate,
    DoctorAvailabilityResponse,
    DoctorAvailabilityBatchUpdate,
    DoctorProfileBase,
    DoctorProfileUpdate,
    DoctorProfileResponse,
    DoctorVerifyRequest,
)
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentStatusUpdate,
    AppointmentResponse,
    AvailableSlot,
)
from app.schemas.query import (
    DoctorResponseCreate,
    DoctorResponseResponse,
    PatientQueryCreate,
    PatientQueryResponse,
)
from app.schemas.consultation import ConsultationCreate, ConsultationUpdate, ConsultationResponse
from app.schemas.record import (
    MedicationItem,
    PrescriptionCreate,
    PrescriptionResponse,
    MedicalRecordCreate,
    MedicalRecordResponse,
)
from app.schemas.notification import NotificationResponse, DeviceTokenRegister

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "TokenPayload",
    "UserResponse",
    "UserStatusUpdate",
    "PatientProfileBase",
    "PatientProfileUpdate",
    "PatientProfileResponse",
    "DoctorAvailabilityBase",
    "DoctorAvailabilityCreate",
    "DoctorAvailabilityResponse",
    "DoctorAvailabilityBatchUpdate",
    "DoctorProfileBase",
    "DoctorProfileUpdate",
    "DoctorProfileResponse",
    "DoctorVerifyRequest",
    "AppointmentCreate",
    "AppointmentReschedule",
    "AppointmentStatusUpdate",
    "AppointmentResponse",
    "AvailableSlot",
    "DoctorResponseCreate",
    "DoctorResponseResponse",
    "PatientQueryCreate",
    "PatientQueryResponse",
    "ConsultationCreate",
    "ConsultationUpdate",
    "ConsultationResponse",
    "MedicationItem",
    "PrescriptionCreate",
    "PrescriptionResponse",
    "MedicalRecordCreate",
    "MedicalRecordResponse",
    "NotificationResponse",
    "DeviceTokenRegister",
]
