from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.doctor import DoctorProfile
from app.models.enums import NotificationType, UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )

    # Hash password
    hashed_pw = get_password_hash(request.password)

    # Create User
    new_user = User(
        email=request.email.lower(),
        hashed_password=hashed_pw,
        full_name=request.full_name,
        phone_number=request.phone_number,
        role=request.role,
        is_active=True,
        is_verified=True if request.role == UserRole.PATIENT else False
    )
    db.add(new_user)
    db.flush()

    # Create associated profile
    if request.role == UserRole.PATIENT:
        patient_profile = PatientProfile(user_id=new_user.id)
        db.add(patient_profile)
    elif request.role == UserRole.DOCTOR:
        doctor_profile = DoctorProfile(
            user_id=new_user.id,
            specialization=request.specialization or "General Medicine",
            license_number=request.license_number or "PENDING",
            department=request.department or "General Medicine",
            years_of_experience=request.years_of_experience or 0,
            bio=request.bio or "",
            consultation_fee=request.consultation_fee or 0.0,
            is_approved=False
        )
        db.add(doctor_profile)

    db.commit()
    db.refresh(new_user)

    # Audit log
    AuditService.log(
        db=db,
        action="USER_REGISTRATION",
        user_id=new_user.id,
        entity_type="User",
        entity_id=str(new_user.id),
        details=f"Registered with role {new_user.role.value}"
    )

    # Welcome notification
    NotificationService.send_notification(
        db=db,
        user_id=new_user.id,
        title="Welcome to HEALORA!",
        message=f"Hello {new_user.full_name}, your HEALORA account has been successfully created.",
        notification_type=NotificationType.ACCOUNT_STATUS
    )

    access_token = create_access_token(subject=new_user.id, role=new_user.role.value)
    refresh_token = create_refresh_token(subject=new_user.id, role=new_user.role.value)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=new_user.role,
        user_id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact support."
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    AuditService.log(
        db=db,
        action="USER_LOGIN",
        user_id=user.id,
        entity_type="User",
        entity_id=str(user.id),
        details="Successful login"
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists"
        )

    new_access_token = create_access_token(subject=user.id, role=user.role.value)
    new_refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
