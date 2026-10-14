from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    appointments,
    auth,
    consultations,
    doctors,
    health,
    notifications,
    patients,
    prescriptions,
    queries,
    records,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(queries.router, prefix="/queries", tags=["Patient Queries & Triage"])
api_router.include_router(consultations.router, prefix="/consultations", tags=["Consultations"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["Prescriptions"])
api_router.include_router(records.router, prefix="/records", tags=["Medical Records"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
