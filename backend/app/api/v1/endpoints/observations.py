import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.observation import Observation
from app.models.inspection import Inspection
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.observation import ObservationCreate, ObservationRevise, ObservationRead
from app.schemas.common import ResponseEnvelope
from app.api.deps import get_current_user

router = APIRouter()

@router.post("", response_model=ResponseEnvelope[ObservationRead], status_code=status.HTTP_201_CREATED)
async def create_observation(
    obs_in: ObservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record an observation (from perception/OCR pipeline or officer input).
    Initializes as revision 1 and is marked as latest.
    """
    ins = await db.execute(select(Inspection).where(Inspection.id == obs_in.inspection_id))
    if not ins.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    obs = Observation(
        **obs_in.model_dump(),
        revision=1,
        is_latest=True,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return ResponseEnvelope(
        success=True,
        message="Observation recorded",
        data=ObservationRead.model_validate(obs)
    )

@router.get("/inspection/{inspection_id}", response_model=ResponseEnvelope[List[ObservationRead]])
async def list_inspection_observations(
    inspection_id: uuid.UUID,
    include_history: bool = Query(False, description="Include previous superseded revisions"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List observations for an inspection.
    By default returns only active latest observations.
    Set include_history=true to inspect historical audit progression.
    """
    query = select(Observation).where(Observation.inspection_id == inspection_id)
    if not include_history:
        query = query.where(Observation.is_latest == True)
    
    result = await db.execute(query.order_by(Observation.observed_at.asc()))
    observations = result.scalars().all()
    return ResponseEnvelope(
        success=True,
        data=[ObservationRead.model_validate(o) for o in observations]
    )

@router.post("/{observation_id}/revise", response_model=ResponseEnvelope[ObservationRead], status_code=status.HTTP_201_CREATED)
async def revise_observation(
    observation_id: uuid.UUID,
    revision_in: ObservationRevise,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adjudicate or correct an observation without overwriting history.
    
    ARCHITECTURAL SAFEGUARD:
    Historical observations are NEVER silently overwritten.
    This creates an immutable new revision (e.g. revision 2), sets prior observation
    is_latest=False, links superseded_by_id, and writes an entry to the AuditLog.
    """
    prior_res = await db.execute(select(Observation).where(Observation.id == observation_id))
    prior_obs = prior_res.scalar_one_or_none()
    if not prior_obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target observation not found")
    
    if not prior_obs.is_latest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revise an observation that has already been superseded by a newer revision."
        )

    # Capture prior state for audit log
    prior_state = {
        "id": str(prior_obs.id),
        "raw_value": prior_obs.raw_value,
        "normalized_value": prior_obs.normalized_value,
        "status": prior_obs.status.value,
        "revision": prior_obs.revision,
    }

    # Create new revision record
    new_obs = Observation(
        inspection_id=prior_obs.inspection_id,
        ocr_region_id=prior_obs.ocr_region_id,
        surface_id=prior_obs.surface_id,
        field_type=prior_obs.field_type,
        raw_value=revision_in.raw_value if revision_in.raw_value is not None else prior_obs.raw_value,
        normalized_value=revision_in.normalized_value if revision_in.normalized_value is not None else prior_obs.normalized_value,
        source=prior_obs.source,
        confidence=1.0,  # Officer verified
        status=revision_in.status,
        bounding_box=prior_obs.bounding_box,
        evidence_reference=prior_obs.evidence_reference,
        package_dimensions=prior_obs.package_dimensions,
        pdp_dimensions=prior_obs.pdp_dimensions,
        character_height=prior_obs.character_height,
        calibration_info=prior_obs.calibration_info,
        measurement_uncertainty=prior_obs.measurement_uncertainty,
        revision=prior_obs.revision + 1,
        is_latest=True,
        revision_reason=revision_in.revision_reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(new_obs)
    await db.flush()  # populate new_obs.id

    # Mark prior observation as superseded
    prior_obs.is_latest = False
    prior_obs.superseded_by_id = new_obs.id

    # Append to tamper-evident audit log
    audit_entry = AuditLog(
        inspection_id=prior_obs.inspection_id,
        user_id=current_user.id,
        action="OBSERVATION_REVISED",
        entity_type="Observation",
        entity_id=str(new_obs.id),
        previous_state=prior_state,
        new_state={
            "id": str(new_obs.id),
            "raw_value": new_obs.raw_value,
            "normalized_value": new_obs.normalized_value,
            "status": new_obs.status.value,
            "revision": new_obs.revision,
        },
        justification=revision_in.revision_reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(new_obs)

    return ResponseEnvelope(
        success=True,
        message=f"Observation revised to revision {new_obs.revision}; prior observation preserved in history",
        data=ObservationRead.model_validate(new_obs)
    )

@router.get("/{observation_id}/history", response_model=ResponseEnvelope[List[ObservationRead]])
async def get_observation_history(
    observation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the full revision chain for an observation.
    """
    obs_res = await db.execute(select(Observation).where(Observation.id == observation_id))
    obs = obs_res.scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")

    # Find all observations for this inspection and field_type to reconstruct chain
    query = (
        select(Observation)
        .where(
            Observation.inspection_id == obs.inspection_id,
            Observation.field_type == obs.field_type
        )
        .order_by(Observation.revision.asc())
    )
    result = await db.execute(query)
    revisions = result.scalars().all()

    return ResponseEnvelope(
        success=True,
        data=[ObservationRead.model_validate(r) for r in revisions]
    )
