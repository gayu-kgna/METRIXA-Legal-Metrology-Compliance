from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.common import ResponseEnvelope

router = APIRouter()

@router.get("/health", response_model=ResponseEnvelope[dict])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic health and database readiness check.
    Confirms active PostgreSQL connection and reports core platform metadata.
    """
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return ResponseEnvelope(
        success=True,
        message="Metrixa API is healthy",
        data={
            "platform": settings.PROJECT_NAME,
            "description": settings.PROJECT_DESCRIPTION,
            "legal_framework": settings.LEGAL_FRAMEWORK,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "database": db_status
        }
    )
