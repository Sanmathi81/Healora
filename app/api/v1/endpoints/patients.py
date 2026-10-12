from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_patient, get_current_user
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.patient import PatientProfileResponse, PatientProfileUpdate
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/profile", response_model=PatientProfileResponse)
def get_my_patient_profile(
    current_patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    return current_patient


@router.put("/profile", response_model=PatientProfileResponse)
def update_my_patient_profile(
    update_data: PatientProfileUpdate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current_patient, key, value)

    db.commit()
    db.refresh(current_patient)

    AuditService.log(
        db=db,
        action="UPDATE_PATIENT_PROFILE",
        user_id=current_patient.user_id,
        entity_type="PatientProfile",
        entity_id=str(current_patient.id),
        details="Patient updated their personal health profile"
    )

    return current_patient


@router.get("/{patient_id}", response_model=PatientProfileResponse)
def get_patient_profile_by_id(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only Doctors, Admins, or the Patient themselves can access this profile
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )

    if current_user.role == UserRole.PATIENT and profile.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view other patients' profiles"
        )

    return profile
