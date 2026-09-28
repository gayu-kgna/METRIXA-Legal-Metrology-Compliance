import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.evidence import AuditLogRead
from app.schemas.common import ResponseEnvelope
from app.api.deps import get_current_user, require_roles

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[List[AuditLogRead]])
async def list_audit_logs(
    inspection_id: Optional[uuid.UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR, UserRole.AUDITOR])),
):
    """
    Retrieve tamper-evident audit logs.
    Restricted to Admins, Adjudicators, and Auditors.
    """
    query = select(AuditLog)
    if inspection_id:
        query = query.where(AuditLog.inspection_id == inspection_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    
    result = await db.execute(query.order_by(AuditLog.performed_at.desc()).limit(100))
    logs = result.scalars().all()
    return ResponseEnvelope(
        success=True,
        data=[AuditLogRead.model_validate(l) for l in logs]
    )
