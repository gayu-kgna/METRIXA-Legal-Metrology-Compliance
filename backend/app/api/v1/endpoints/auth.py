from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.schemas.common import ResponseEnvelope
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=ResponseEnvelope[UserRead], status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new officer or user account."""
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        badge_number=user_in.badge_number,
        jurisdiction=user_in.jurisdiction,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return ResponseEnvelope(
        success=True,
        message="User successfully registered",
        data=UserRead.model_validate(new_user)
    )

@router.post("/login", response_model=ResponseEnvelope[TokenResponse])
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate officer credentials and return JWT bearer token."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    
    return ResponseEnvelope(
        success=True,
        message="Authentication successful",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserRead.model_validate(user)
        )
    )

@router.get("/me", response_model=ResponseEnvelope[UserRead])
async def get_current_officer(current_user: User = Depends(get_current_user)):
    """Get currently authenticated officer profile."""
    return ResponseEnvelope(
        success=True,
        data=UserRead.model_validate(current_user)
    )
