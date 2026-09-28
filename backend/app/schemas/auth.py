import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from app.models.enums import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserRead"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.INSPECTOR
    badge_number: Optional[str] = None
    jurisdiction: Optional[str] = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    badge_number: Optional[str] = None
    jurisdiction: Optional[str] = None
    is_active: bool
    created_at: datetime

TokenResponse.model_rebuild()
