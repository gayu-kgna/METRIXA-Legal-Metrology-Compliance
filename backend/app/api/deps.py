import uuid
from typing import AsyncGenerator, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return user

def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role {current_user.role.value}",
            )
        return current_user
    return role_checker

from app.services.storage import get_storage_service, BaseStorageService
from app.services.image_ingestion import ImageIngestionService
from app.services.cv.preprocessing import CVPreprocessingService
from app.services.ocr.service import OCRProcessingService

def get_image_ingestion_service(
    storage_service: BaseStorageService = Depends(get_storage_service)
) -> ImageIngestionService:
    return ImageIngestionService(storage_service=storage_service)

def get_cv_preprocessing_service(
    storage_service: BaseStorageService = Depends(get_storage_service)
) -> CVPreprocessingService:
    return CVPreprocessingService(storage_service=storage_service)

def get_ocr_processing_service(
    storage_service: BaseStorageService = Depends(get_storage_service),
    cv_service: CVPreprocessingService = Depends(get_cv_preprocessing_service),
) -> OCRProcessingService:
    return OCRProcessingService(storage_service=storage_service, cv_service=cv_service)

from app.services.entity.parser import EntityParsingService
from app.services.geometry.pdp import PDPGeometryService

def get_entity_parsing_service() -> EntityParsingService:
    return EntityParsingService()

def get_pdp_geometry_service() -> PDPGeometryService:
    return PDPGeometryService()

from app.services.rules.engine import DeterministicRuleEngine
from app.services.evidence.service import EvidenceService
from app.services.report.pdf_generator import DossierPDFGenerator

def get_rule_engine_service() -> DeterministicRuleEngine:
    return DeterministicRuleEngine()

def get_evidence_service() -> EvidenceService:
    return EvidenceService()

def get_pdf_generator(
    storage_service: BaseStorageService = Depends(get_storage_service)
) -> DossierPDFGenerator:
    return DossierPDFGenerator(storage_service=storage_service)

