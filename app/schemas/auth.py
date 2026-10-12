from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    role: UserRole = UserRole.PATIENT

    # Doctor-specific registration fields (required if role is DOCTOR)
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    years_of_experience: Optional[int] = 0
    bio: Optional[str] = None
    consultation_fee: Optional[float] = 0.0


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    email: str


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    exp: int
