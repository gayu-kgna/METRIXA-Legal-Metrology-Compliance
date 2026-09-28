import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.adjudication import OCRAdjudication
from app.models.observation import Observation
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.enums import UserRole, ObservationStatus, ObservationSource, CorrectionType, RuleOutcome, FieldType
from app.schemas.common import ResponseEnvelope
from app.schemas.observation import ObservationRead
from app.schemas.rule import RuleEvaluationRead
from app.schemas.adjudication import (
    OCRRegionPatchRequest,
    OCRRegionCreateRequest,
    OCRRegionRejectRequest,
    OCRAdjudicationRead,
    AdjudicatedOCRRegion,
    ManualObservationCreateRequest,
    ObservationVerifyRequest,
    ObservationCorrectRequest,
    ObservationRejectRequest,
    ObservationStatusUpdateRequest,
    ConflictGroup,
    AdjudicationWorkspaceState,
    RuleEvaluationChange,
    RuleReevaluationResponse,
)
from app.api.deps import get_current_user, get_rule_engine_service
from app.services.rules.engine import DeterministicRuleEngine

router = APIRouter()

def _verify_adjudication_access(inspection: Inspection, current_user: User):
    """
    Enforce RBAC:
    Adjudicators, Admins, and Auditors can adjudicate any inspection.
    Inspectors can adjudicate inspections assigned to them.
    Other users or non-assigned inspectors receive 403 Forbidden.
    """
    if current_user.role in [UserRole.ADJUDICATOR, UserRole.ADMIN, UserRole.AUDITOR]:
        return
    if current_user.role == UserRole.INSPECTOR and inspection.inspector_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: You do not have permission to adjudicate this inspection."
    )

async def _get_inspection_or_404(inspection_id: uuid.UUID, db: AsyncSession, current_user: User) -> Inspection:
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    _verify_adjudication_access(inspection, current_user)
    return inspection

# --------------------------------------------------------------------------
# 1. Consolidated Adjudication Workspace
# --------------------------------------------------------------------------

@router.get(
    "/{inspection_id}/adjudication",
    response_model=ResponseEnvelope[AdjudicationWorkspaceState],
    summary="Retrieve consolidated adjudication workspace data",
)
async def get_adjudication_workspace(
    inspection_id: uuid.UUID,
    surface_id: Optional[uuid.UUID] = Query(None, description="Filter for a specific surface"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    # 1. Surfaces
    surf_res = await db.execute(
        select(InspectionSurface)
        .where(InspectionSurface.inspection_id == inspection_id)
        .order_by(InspectionSurface.captured_at.asc())
    )
    surfaces = surf_res.scalars().all()
    surfaces_data = [
        {
            "id": s.id,
            "surface_type": s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type),
            "original_filename": s.original_filename,
            "image_width": s.image_width,
            "image_height": s.image_height,
            "sha256_hash": s.sha256_hash,
            "captured_at": s.captured_at,
        }
        for s in surfaces
    ]

    selected_surface_id = surface_id or (surfaces[0].id if surfaces else None)

    # 2. OCR Runs
    ocr_query = select(OCRRun).where(OCRRun.inspection_id == inspection_id)
    if selected_surface_id:
        ocr_query = ocr_query.where(OCRRun.surface_id == selected_surface_id)
    ocr_res = await db.execute(ocr_query.order_by(OCRRun.executed_at.desc()))
    ocr_runs = ocr_res.scalars().all()
    ocr_runs_data = [
        {
            "id": r.id,
            "surface_id": r.surface_id,
            "provider_name": r.provider_name,
            "preprocessing_variant": r.preprocessing_variant,
            "status": r.status,
            "total_regions_detected": r.total_regions_detected,
            "executed_at": r.executed_at,
        }
        for r in ocr_runs
    ]

    # 3. OCR Regions & Active Adjudications
    regions_query = (
        select(OCRRegion)
        .join(InspectionSurface, OCRRegion.surface_id == InspectionSurface.id)
        .where(InspectionSurface.inspection_id == inspection_id)
    )
    if selected_surface_id:
        regions_query = regions_query.where(OCRRegion.surface_id == selected_surface_id)
    reg_res = await db.execute(regions_query.order_by(OCRRegion.token_order.asc()))
    base_regions = reg_res.scalars().all()

    # Active adjudications for this inspection
    adj_query = (
        select(OCRAdjudication)
        .options(selectinload(OCRAdjudication.created_by))
        .where(OCRAdjudication.inspection_id == inspection_id, OCRAdjudication.is_active == True)
    )
    if selected_surface_id:
        adj_query = adj_query.where(OCRAdjudication.surface_id == selected_surface_id)
    adj_res = await db.execute(adj_query)
    adjudications = adj_res.scalars().all()

    # Map adjudications by ocr_region_id
    adj_by_region: Dict[uuid.UUID, OCRAdjudication] = {}
    manual_adjs: List[OCRAdjudication] = []
    for adj in adjudications:
        if adj.ocr_region_id:
            adj_by_region[adj.ocr_region_id] = adj
        elif adj.correction_type == CorrectionType.REGION_CREATED:
            manual_adjs.append(adj)

    # Also map observations by ocr_region_id for linking
    obs_query = select(Observation).where(Observation.inspection_id == inspection_id, Observation.is_latest == True)
    obs_res = await db.execute(obs_query.order_by(Observation.observed_at.asc()))
    observations = obs_res.scalars().all()
    obs_by_region = {o.ocr_region_id: o for o in observations if o.ocr_region_id}

    adjudicated_regions: List[AdjudicatedOCRRegion] = []
    for reg in base_regions:
        adj = adj_by_region.get(reg.id)
        linked_obs = obs_by_region.get(reg.id)

        if adj:
            adjudicated_regions.append(
                AdjudicatedOCRRegion(
                    id=reg.id,
                    surface_id=reg.surface_id,
                    ocr_run_id=reg.ocr_run_id,
                    raw_text=adj.corrected_text if adj.corrected_text is not None else reg.raw_text,
                    original_text=reg.raw_text,
                    confidence=adj.original_confidence,
                    bounding_box=adj.corrected_bounding_box if adj.corrected_bounding_box else reg.bounding_box,
                    original_bounding_box=reg.bounding_box,
                    status=adj.status,
                    correction_type=adj.correction_type.value if hasattr(adj.correction_type, "value") else str(adj.correction_type),
                    is_adjudicated=True,
                    adjudication_id=adj.id,
                    revision=adj.revision,
                    reason=adj.reason,
                    adjudicated_by=adj.created_by.full_name if adj.created_by else None,
                    adjudicated_at=adj.adjudicated_at,
                    linked_observation_id=linked_obs.id if linked_obs else None,
                    linked_field_type=linked_obs.field_type.value if linked_obs and hasattr(linked_obs.field_type, "value") else (str(linked_obs.field_type) if linked_obs else None),
                )
            )
        else:
            adjudicated_regions.append(
                AdjudicatedOCRRegion(
                    id=reg.id,
                    surface_id=reg.surface_id,
                    ocr_run_id=reg.ocr_run_id,
                    raw_text=reg.raw_text,
                    original_text=reg.raw_text,
                    confidence=reg.confidence,
                    bounding_box=reg.bounding_box,
                    original_bounding_box=reg.bounding_box,
                    status="ORIGINAL",
                    correction_type=None,
                    is_adjudicated=False,
                    adjudication_id=None,
                    revision=1,
                    reason=None,
                    adjudicated_by=None,
                    adjudicated_at=None,
                    linked_observation_id=linked_obs.id if linked_obs else None,
                    linked_field_type=linked_obs.field_type.value if linked_obs and hasattr(linked_obs.field_type, "value") else (str(linked_obs.field_type) if linked_obs else None),
                )
            )

    # Append manual regions
    for m in manual_adjs:
        adjudicated_regions.append(
            AdjudicatedOCRRegion(
                id=m.id,
                surface_id=m.surface_id,
                ocr_run_id=m.ocr_run_id,
                raw_text=m.corrected_text or "",
                original_text="",
                confidence=1.0,
                bounding_box=m.corrected_bounding_box,
                original_bounding_box=m.corrected_bounding_box,
                status="MANUAL",
                correction_type=CorrectionType.REGION_CREATED.value,
                is_adjudicated=True,
                adjudication_id=m.id,
                revision=m.revision,
                reason=m.reason,
                adjudicated_by=m.created_by.full_name if m.created_by else None,
                adjudicated_at=m.adjudicated_at,
                linked_observation_id=None,
                linked_field_type=None,
            )
        )

    # 4. Conflict Analysis
    obs_by_field: Dict[FieldType, List[Observation]] = {}
    for o in observations:
        obs_by_field.setdefault(o.field_type, []).append(o)

    conflict_groups: List[ConflictGroup] = []
    for ftype, obs_list in obs_by_field.items():
        distinct_raw = set(o.raw_value.strip().lower() for o in obs_list if o.status != ObservationStatus.REJECTED)
        has_conflict = len(distinct_raw) > 1 or any(o.status == ObservationStatus.CONFLICTING for o in obs_list)
        msg = f"Conflicting observations detected ({len(distinct_raw)} differing values)" if has_conflict else None

        f_label = ftype.value if hasattr(ftype, "value") else str(ftype)
        conflict_groups.append(
            ConflictGroup(
                field_type=ftype,
                field_label=f_label.replace("_", " ").title(),
                has_conflict=has_conflict,
                conflict_message=msg,
                observations=[ObservationRead.model_validate(o) for o in obs_list],
            )
        )

    # 5. Latest Rule Evaluations
    latest_eval_run_id_res = await db.execute(
        select(RuleEvaluation.evaluation_run_id)
        .where(RuleEvaluation.inspection_id == inspection_id)
        .order_by(RuleEvaluation.evaluated_at.desc())
        .limit(1)
    )
    latest_eval_run_id = latest_eval_run_id_res.scalar_one_or_none()

    eval_reads: List[RuleEvaluationRead] = []
    if latest_eval_run_id:
        evals_res = await db.execute(
            select(RuleEvaluation)
            .options(selectinload(RuleEvaluation.rule_definition))
            .where(RuleEvaluation.inspection_id == inspection_id, RuleEvaluation.evaluation_run_id == latest_eval_run_id)
            .order_by(RuleEvaluation.rule_definition_id.asc())
        )
        evals = evals_res.scalars().all()
        eval_reads = [RuleEvaluationRead.model_validate(e) for e in evals]

    # 6. Audit History
    audit_res = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.inspection_id == inspection_id)
        .order_by(AuditLog.performed_at.desc())
        .limit(30)
    )
    audit_logs = audit_res.scalars().all()
    audit_history_data = [
        {
            "id": a.id,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "justification": a.justification,
            "user_name": a.user.full_name if a.user else "System",
            "performed_at": a.performed_at,
            "previous_state": a.previous_state,
            "new_state": a.new_state,
        }
        for a in audit_logs
    ]

    return ResponseEnvelope(
        success=True,
        data=AdjudicationWorkspaceState(
            inspection_id=inspection.id,
            inspection_number=inspection.inspection_number,
            surfaces=surfaces_data,
            active_surface_id=selected_surface_id,
            ocr_runs=ocr_runs_data,
            regions=adjudicated_regions,
            observations=[ObservationRead.model_validate(o) for o in observations],
            conflicts=conflict_groups,
            latest_evaluations=eval_reads,
            evaluation_run_id=latest_eval_run_id,
            audit_history=audit_history_data,
        )
    )

# --------------------------------------------------------------------------
# 2. OCR Region Adjudication Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/{inspection_id}/images/{image_id}/ocr-regions",
    response_model=ResponseEnvelope[List[AdjudicatedOCRRegion]],
    summary="List OCR regions with applied human adjudications for an image",
)
async def get_surface_ocr_regions(
    inspection_id: uuid.UUID,
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    reg_res = await db.execute(
        select(OCRRegion)
        .where(OCRRegion.surface_id == image_id)
        .order_by(OCRRegion.token_order.asc())
    )
    regions = reg_res.scalars().all()

    adj_res = await db.execute(
        select(OCRAdjudication)
        .options(selectinload(OCRAdjudication.created_by))
        .where(
            OCRAdjudication.inspection_id == inspection_id,
            OCRAdjudication.surface_id == image_id,
            OCRAdjudication.is_active == True,
        )
    )
    adjudications = adj_res.scalars().all()

    adj_by_region = {a.ocr_region_id: a for a in adjudications if a.ocr_region_id}
    manual_adjs = [a for a in adjudications if not a.ocr_region_id and a.correction_type == CorrectionType.REGION_CREATED]

    obs_res = await db.execute(
        select(Observation).where(Observation.inspection_id == inspection_id, Observation.is_latest == True)
    )
    obs_by_region = {o.ocr_region_id: o for o in obs_res.scalars().all() if o.ocr_region_id}

    result: List[AdjudicatedOCRRegion] = []
    for reg in regions:
        adj = adj_by_region.get(reg.id)
        linked_obs = obs_by_region.get(reg.id)
        if adj:
            result.append(
                AdjudicatedOCRRegion(
                    id=reg.id,
                    surface_id=reg.surface_id,
                    ocr_run_id=reg.ocr_run_id,
                    raw_text=adj.corrected_text if adj.corrected_text is not None else reg.raw_text,
                    original_text=reg.raw_text,
                    confidence=adj.original_confidence,
                    bounding_box=adj.corrected_bounding_box if adj.corrected_bounding_box else reg.bounding_box,
                    original_bounding_box=reg.bounding_box,
                    status=adj.status,
                    correction_type=adj.correction_type.value if hasattr(adj.correction_type, "value") else str(adj.correction_type),
                    is_adjudicated=True,
                    adjudication_id=adj.id,
                    revision=adj.revision,
                    reason=adj.reason,
                    adjudicated_by=adj.created_by.full_name if adj.created_by else None,
                    adjudicated_at=adj.adjudicated_at,
                    linked_observation_id=linked_obs.id if linked_obs else None,
                    linked_field_type=linked_obs.field_type.value if linked_obs and hasattr(linked_obs.field_type, "value") else (str(linked_obs.field_type) if linked_obs else None),
                )
            )
        else:
            result.append(
                AdjudicatedOCRRegion(
                    id=reg.id,
                    surface_id=reg.surface_id,
                    ocr_run_id=reg.ocr_run_id,
                    raw_text=reg.raw_text,
                    original_text=reg.raw_text,
                    confidence=reg.confidence,
                    bounding_box=reg.bounding_box,
                    original_bounding_box=reg.bounding_box,
                    status="ORIGINAL",
                    correction_type=None,
                    is_adjudicated=False,
                    adjudication_id=None,
                    revision=1,
                    reason=None,
                    adjudicated_by=None,
                    adjudicated_at=None,
                    linked_observation_id=linked_obs.id if linked_obs else None,
                    linked_field_type=linked_obs.field_type.value if linked_obs and hasattr(linked_obs.field_type, "value") else (str(linked_obs.field_type) if linked_obs else None),
                )
            )

    for m in manual_adjs:
        result.append(
            AdjudicatedOCRRegion(
                id=m.id,
                surface_id=m.surface_id,
                ocr_run_id=m.ocr_run_id,
                raw_text=m.corrected_text or "",
                original_text="",
                confidence=1.0,
                bounding_box=m.corrected_bounding_box,
                original_bounding_box=m.corrected_bounding_box,
                status="MANUAL",
                correction_type=CorrectionType.REGION_CREATED.value,
                is_adjudicated=True,
                adjudication_id=m.id,
                revision=m.revision,
                reason=m.reason,
                adjudicated_by=m.created_by.full_name if m.created_by else None,
                adjudicated_at=m.adjudicated_at,
                linked_observation_id=None,
                linked_field_type=None,
            )
        )

    return ResponseEnvelope(success=True, data=result)

@router.post(
    "/{inspection_id}/ocr-regions",
    response_model=ResponseEnvelope[AdjudicatedOCRRegion],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new manual OCR bounding box region",
)
async def create_manual_ocr_region(
    inspection_id: uuid.UUID,
    payload: OCRRegionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    # Verify surface belongs to inspection
    surf_res = await db.execute(
        select(InspectionSurface).where(
            InspectionSurface.id == payload.surface_id,
            InspectionSurface.inspection_id == inspection_id,
        )
    )
    surface = surf_res.scalar_one_or_none()
    if not surface:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Surface not found for this inspection")

    adj = OCRAdjudication(
        inspection_id=inspection_id,
        surface_id=payload.surface_id,
        ocr_run_id=payload.ocr_run_id,
        ocr_region_id=None,
        parent_adjudication_id=None,
        correction_type=CorrectionType.REGION_CREATED,
        status="MANUAL",
        original_text=None,
        corrected_text=payload.raw_text,
        original_bounding_box={},
        corrected_bounding_box=payload.bounding_box.model_dump(),
        original_confidence=1.0,
        reason=payload.reason,
        created_by_id=current_user.id,
        revision=1,
        is_active=True,
        adjudicated_at=datetime.now(timezone.utc),
    )
    db.add(adj)
    await db.flush()

    # Append to AuditLog
    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OCR_REGION_CREATED",
        entity_type="OCRAdjudication",
        entity_id=str(adj.id),
        previous_state={},
        new_state={
            "id": str(adj.id),
            "surface_id": str(adj.surface_id),
            "text": adj.corrected_text,
            "bounding_box": adj.corrected_bounding_box,
            "status": "MANUAL",
        },
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(adj)

    return ResponseEnvelope(
        success=True,
        message="Manual region created successfully",
        data=AdjudicatedOCRRegion(
            id=adj.id,
            surface_id=adj.surface_id,
            ocr_run_id=adj.ocr_run_id,
            raw_text=adj.corrected_text or "",
            original_text="",
            confidence=1.0,
            bounding_box=adj.corrected_bounding_box,
            original_bounding_box={},
            status="MANUAL",
            correction_type=CorrectionType.REGION_CREATED.value,
            is_adjudicated=True,
            adjudication_id=adj.id,
            revision=1,
            reason=adj.reason,
            adjudicated_by=current_user.full_name,
            adjudicated_at=adj.adjudicated_at,
        ),
    )

@router.patch(
    "/{inspection_id}/ocr-regions/{region_id}",
    response_model=ResponseEnvelope[AdjudicatedOCRRegion],
    summary="Correct text and/or bounding box of an OCR region (immutable)",
)
async def patch_ocr_region(
    inspection_id: uuid.UUID,
    region_id: uuid.UUID,
    payload: OCRRegionPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    # Check if region is in ocr_regions or is a manual ocr_adjudications record
    reg_res = await db.execute(select(OCRRegion).where(OCRRegion.id == region_id))
    original_region = reg_res.scalar_one_or_none()

    manual_adj: Optional[OCRAdjudication] = None
    if not original_region:
        m_res = await db.execute(select(OCRAdjudication).where(OCRAdjudication.id == region_id, OCRAdjudication.inspection_id == inspection_id))
        manual_adj = m_res.scalar_one_or_none()
        if not manual_adj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target OCR region not found")

    surface_id = original_region.surface_id if original_region else manual_adj.surface_id
    ocr_run_id = original_region.ocr_run_id if original_region else manual_adj.ocr_run_id

    # Find prior active adjudication
    prior_adj_res = await db.execute(
        select(OCRAdjudication).where(
            OCRAdjudication.inspection_id == inspection_id,
            OCRAdjudication.is_active == True,
            (OCRAdjudication.ocr_region_id == region_id) if original_region else (OCRAdjudication.id == region_id),
        )
    )
    prior_adj = prior_adj_res.scalar_one_or_none()

    if prior_adj:
        prior_adj.is_active = False

    orig_text = original_region.raw_text if original_region else (manual_adj.corrected_text or "")
    orig_box = original_region.bounding_box if original_region else manual_adj.corrected_bounding_box
    orig_conf = original_region.confidence if original_region else manual_adj.original_confidence

    new_text = payload.raw_text if payload.raw_text is not None else (prior_adj.corrected_text if prior_adj else orig_text)
    new_box = payload.bounding_box.model_dump() if payload.bounding_box is not None else (prior_adj.corrected_bounding_box if prior_adj else orig_box)

    # Determine correction type
    if payload.bounding_box is not None and payload.raw_text is not None:
        corr_type = CorrectionType.BOUNDING_BOX_CORRECTION
    elif payload.bounding_box is not None:
        corr_type = CorrectionType.BOUNDING_BOX_CORRECTION
    else:
        corr_type = CorrectionType.TEXT_CORRECTION

    rev_num = (prior_adj.revision + 1) if prior_adj else 1

    new_adj = OCRAdjudication(
        inspection_id=inspection_id,
        surface_id=surface_id,
        ocr_run_id=ocr_run_id,
        ocr_region_id=original_region.id if original_region else None,
        parent_adjudication_id=prior_adj.id if prior_adj else (manual_adj.id if manual_adj else None),
        correction_type=corr_type,
        status="CORRECTED" if original_region else "MANUAL",
        original_text=orig_text,
        corrected_text=new_text,
        original_bounding_box=orig_box,
        corrected_bounding_box=new_box,
        original_confidence=orig_conf,
        reason=payload.reason,
        created_by_id=current_user.id,
        revision=rev_num,
        is_active=True,
        adjudicated_at=datetime.now(timezone.utc),
    )
    db.add(new_adj)
    await db.flush()

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OCR_REGION_EDITED",
        entity_type="OCRAdjudication",
        entity_id=str(new_adj.id),
        previous_state={
            "text": orig_text,
            "bounding_box": orig_box,
            "revision": prior_adj.revision if prior_adj else 0,
        },
        new_state={
            "text": new_text,
            "bounding_box": new_box,
            "revision": rev_num,
            "status": new_adj.status,
            "correction_type": corr_type.value,
        },
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_adj)

    return ResponseEnvelope(
        success=True,
        message=f"OCR region adjudicated to revision {rev_num}",
        data=AdjudicatedOCRRegion(
            id=original_region.id if original_region else new_adj.id,
            surface_id=surface_id,
            ocr_run_id=ocr_run_id,
            raw_text=new_text,
            original_text=orig_text,
            confidence=orig_conf,
            bounding_box=new_box,
            original_bounding_box=orig_box,
            status=new_adj.status,
            correction_type=corr_type.value,
            is_adjudicated=True,
            adjudication_id=new_adj.id,
            revision=rev_num,
            reason=new_adj.reason,
            adjudicated_by=current_user.full_name,
            adjudicated_at=new_adj.adjudicated_at,
        ),
    )

@router.post(
    "/{inspection_id}/ocr-regions/{region_id}/reject",
    response_model=ResponseEnvelope[AdjudicatedOCRRegion],
    summary="Reject an OCR region without destroying historical OCR",
)
async def reject_ocr_region(
    inspection_id: uuid.UUID,
    region_id: uuid.UUID,
    payload: OCRRegionRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    reg_res = await db.execute(select(OCRRegion).where(OCRRegion.id == region_id))
    original_region = reg_res.scalar_one_or_none()

    manual_adj: Optional[OCRAdjudication] = None
    if not original_region:
        m_res = await db.execute(select(OCRAdjudication).where(OCRAdjudication.id == region_id, OCRAdjudication.inspection_id == inspection_id))
        manual_adj = m_res.scalar_one_or_none()
        if not manual_adj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target OCR region not found")

    surface_id = original_region.surface_id if original_region else manual_adj.surface_id
    ocr_run_id = original_region.ocr_run_id if original_region else manual_adj.ocr_run_id

    # Deactivate prior adjudication
    prior_adj_res = await db.execute(
        select(OCRAdjudication).where(
            OCRAdjudication.inspection_id == inspection_id,
            OCRAdjudication.is_active == True,
            (OCRAdjudication.ocr_region_id == region_id) if original_region else (OCRAdjudication.id == region_id),
        )
    )
    prior_adj = prior_adj_res.scalar_one_or_none()
    if prior_adj:
        prior_adj.is_active = False

    orig_text = original_region.raw_text if original_region else (manual_adj.corrected_text or "")
    orig_box = original_region.bounding_box if original_region else manual_adj.corrected_bounding_box
    rev_num = (prior_adj.revision + 1) if prior_adj else 1

    reject_adj = OCRAdjudication(
        inspection_id=inspection_id,
        surface_id=surface_id,
        ocr_run_id=ocr_run_id,
        ocr_region_id=original_region.id if original_region else None,
        parent_adjudication_id=prior_adj.id if prior_adj else (manual_adj.id if manual_adj else None),
        correction_type=CorrectionType.REGION_REJECTED,
        status="REJECTED",
        original_text=orig_text,
        corrected_text=orig_text,
        original_bounding_box=orig_box,
        corrected_bounding_box=orig_box,
        original_confidence=0.0,
        reason=payload.reason,
        created_by_id=current_user.id,
        revision=rev_num,
        is_active=True,
        adjudicated_at=datetime.now(timezone.utc),
    )
    db.add(reject_adj)
    await db.flush()

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OCR_REGION_REJECTED",
        entity_type="OCRAdjudication",
        entity_id=str(reject_adj.id),
        previous_state={"text": orig_text, "status": "ORIGINAL"},
        new_state={"status": "REJECTED", "reason": payload.reason},
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(reject_adj)

    return ResponseEnvelope(
        success=True,
        message="OCR region marked as rejected",
        data=AdjudicatedOCRRegion(
            id=original_region.id if original_region else reject_adj.id,
            surface_id=surface_id,
            ocr_run_id=ocr_run_id,
            raw_text=orig_text,
            original_text=orig_text,
            confidence=0.0,
            bounding_box=orig_box,
            original_bounding_box=orig_box,
            status="REJECTED",
            correction_type=CorrectionType.REGION_REJECTED.value,
            is_adjudicated=True,
            adjudication_id=reject_adj.id,
            revision=rev_num,
            reason=payload.reason,
            adjudicated_by=current_user.full_name,
            adjudicated_at=reject_adj.adjudicated_at,
        ),
    )

# --------------------------------------------------------------------------
# 3. Observation Adjudication Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/{inspection_id}/observations",
    response_model=ResponseEnvelope[List[ObservationRead]],
    summary="List active observations for an inspection",
)
async def list_adjudicated_observations(
    inspection_id: uuid.UUID,
    include_superseded: bool = Query(False, description="Include historical superseded revisions"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)

    query = select(Observation).where(Observation.inspection_id == inspection_id)
    if not include_superseded:
        query = query.where(Observation.is_latest == True)

    res = await db.execute(query.order_by(Observation.observed_at.asc()))
    obs_list = res.scalars().all()
    return ResponseEnvelope(
        success=True,
        data=[ObservationRead.model_validate(o) for o in obs_list]
    )

@router.post(
    "/{inspection_id}/observations/manual",
    response_model=ResponseEnvelope[ObservationRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual statutory observation with officer provenance",
)
async def create_manual_observation(
    inspection_id: uuid.UUID,
    payload: ManualObservationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    norm_val = payload.normalized_value or {"display": payload.raw_value, "manual_input": True}
    bbox = payload.bounding_box.model_dump() if payload.bounding_box else {}

    obs = Observation(
        inspection_id=inspection_id,
        ocr_region_id=payload.ocr_region_id,
        surface_id=payload.surface_id,
        field_type=payload.field_type,
        raw_value=payload.raw_value,
        normalized_value=norm_val,
        source=ObservationSource.OFFICER_INPUT,
        confidence=1.0,
        status=ObservationStatus.VERIFIED,
        bounding_box=bbox,
        revision=1,
        is_latest=True,
        revision_reason=payload.reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(obs)
    await db.flush()

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="MANUAL_OBSERVATION_CREATED",
        entity_type="Observation",
        entity_id=str(obs.id),
        previous_state={},
        new_state={
            "id": str(obs.id),
            "field_type": obs.field_type.value,
            "raw_value": obs.raw_value,
            "source": obs.source.value,
            "status": obs.status.value,
        },
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(obs)

    return ResponseEnvelope(
        success=True,
        message=f"Manual observation created for {payload.field_type.value}",
        data=ObservationRead.model_validate(obs)
    )

@router.post(
    "/{inspection_id}/observations/{observation_id}/verify",
    response_model=ResponseEnvelope[ObservationRead],
    summary="Accept and verify an extracted observation",
)
async def verify_observation(
    inspection_id: uuid.UUID,
    observation_id: uuid.UUID,
    payload: Optional[ObservationVerifyRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)
    reason = payload.reason if payload and payload.reason else "Inspector accepted and verified observation"

    res = await db.execute(
        select(Observation).where(Observation.id == observation_id, Observation.inspection_id == inspection_id)
    )
    prior_obs = res.scalar_one_or_none()
    if not prior_obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target observation not found")

    if not prior_obs.is_latest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot verify a superseded observation revision")

    # If already verified, return idempotent
    if prior_obs.status == ObservationStatus.VERIFIED and prior_obs.confidence == 1.0:
        return ResponseEnvelope(success=True, message="Observation already verified", data=ObservationRead.model_validate(prior_obs))

    new_obs = Observation(
        inspection_id=prior_obs.inspection_id,
        ocr_region_id=prior_obs.ocr_region_id,
        surface_id=prior_obs.surface_id,
        entity_run_id=prior_obs.entity_run_id,
        field_type=prior_obs.field_type,
        raw_value=prior_obs.raw_value,
        normalized_value=prior_obs.normalized_value,
        source=prior_obs.source,
        confidence=1.0,
        status=ObservationStatus.VERIFIED,
        bounding_box=prior_obs.bounding_box,
        evidence_reference=prior_obs.evidence_reference,
        package_dimensions=prior_obs.package_dimensions,
        pdp_dimensions=prior_obs.pdp_dimensions,
        character_height=prior_obs.character_height,
        calibration_info=prior_obs.calibration_info,
        measurement_uncertainty=prior_obs.measurement_uncertainty,
        revision=prior_obs.revision + 1,
        is_latest=True,
        revision_reason=reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(new_obs)
    await db.flush()

    prior_obs.is_latest = False
    prior_obs.superseded_by_id = new_obs.id

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OBSERVATION_VERIFIED",
        entity_type="Observation",
        entity_id=str(new_obs.id),
        previous_state={"status": prior_obs.status.value, "confidence": prior_obs.confidence, "revision": prior_obs.revision},
        new_state={"status": new_obs.status.value, "confidence": 1.0, "revision": new_obs.revision},
        justification=reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_obs)

    return ResponseEnvelope(
        success=True,
        message=f"Observation verified (revision {new_obs.revision})",
        data=ObservationRead.model_validate(new_obs)
    )

@router.post(
    "/{inspection_id}/observations/{observation_id}/correct",
    response_model=ResponseEnvelope[ObservationRead],
    summary="Correct an observation's raw and/or normalized value (immutable revision)",
)
async def correct_observation(
    inspection_id: uuid.UUID,
    observation_id: uuid.UUID,
    payload: ObservationCorrectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)

    res = await db.execute(
        select(Observation).where(Observation.id == observation_id, Observation.inspection_id == inspection_id)
    )
    prior_obs = res.scalar_one_or_none()
    if not prior_obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target observation not found")

    if not prior_obs.is_latest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot correct a superseded observation revision")

    new_raw = payload.raw_value if payload.raw_value is not None else prior_obs.raw_value
    new_norm = payload.normalized_value if payload.normalized_value is not None else prior_obs.normalized_value

    new_obs = Observation(
        inspection_id=prior_obs.inspection_id,
        ocr_region_id=prior_obs.ocr_region_id,
        surface_id=prior_obs.surface_id,
        entity_run_id=prior_obs.entity_run_id,
        field_type=prior_obs.field_type,
        raw_value=new_raw,
        normalized_value=new_norm,
        source=prior_obs.source,
        confidence=1.0,
        status=ObservationStatus.VERIFIED,
        bounding_box=prior_obs.bounding_box,
        evidence_reference=prior_obs.evidence_reference,
        package_dimensions=prior_obs.package_dimensions,
        pdp_dimensions=prior_obs.pdp_dimensions,
        character_height=prior_obs.character_height,
        calibration_info=prior_obs.calibration_info,
        measurement_uncertainty=prior_obs.measurement_uncertainty,
        revision=prior_obs.revision + 1,
        is_latest=True,
        revision_reason=payload.reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(new_obs)
    await db.flush()

    prior_obs.is_latest = False
    prior_obs.superseded_by_id = new_obs.id

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OBSERVATION_CORRECTED",
        entity_type="Observation",
        entity_id=str(new_obs.id),
        previous_state={"raw_value": prior_obs.raw_value, "status": prior_obs.status.value, "revision": prior_obs.revision},
        new_state={"raw_value": new_raw, "status": new_obs.status.value, "revision": new_obs.revision},
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_obs)

    return ResponseEnvelope(
        success=True,
        message=f"Observation corrected to revision {new_obs.revision}",
        data=ObservationRead.model_validate(new_obs)
    )

@router.post(
    "/{inspection_id}/observations/{observation_id}/reject",
    response_model=ResponseEnvelope[ObservationRead],
    summary="Reject an observation without destroying historical record",
)
async def reject_observation(
    inspection_id: uuid.UUID,
    observation_id: uuid.UUID,
    payload: ObservationRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)

    res = await db.execute(
        select(Observation).where(Observation.id == observation_id, Observation.inspection_id == inspection_id)
    )
    prior_obs = res.scalar_one_or_none()
    if not prior_obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target observation not found")

    if not prior_obs.is_latest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reject a superseded observation revision")

    new_obs = Observation(
        inspection_id=prior_obs.inspection_id,
        ocr_region_id=prior_obs.ocr_region_id,
        surface_id=prior_obs.surface_id,
        entity_run_id=prior_obs.entity_run_id,
        field_type=prior_obs.field_type,
        raw_value=prior_obs.raw_value,
        normalized_value=prior_obs.normalized_value,
        source=prior_obs.source,
        confidence=0.0,
        status=ObservationStatus.REJECTED,
        bounding_box=prior_obs.bounding_box,
        evidence_reference=prior_obs.evidence_reference,
        package_dimensions=prior_obs.package_dimensions,
        pdp_dimensions=prior_obs.pdp_dimensions,
        character_height=prior_obs.character_height,
        calibration_info=prior_obs.calibration_info,
        measurement_uncertainty=prior_obs.measurement_uncertainty,
        revision=prior_obs.revision + 1,
        is_latest=True,
        revision_reason=payload.reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(new_obs)
    await db.flush()

    prior_obs.is_latest = False
    prior_obs.superseded_by_id = new_obs.id

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OBSERVATION_REJECTED",
        entity_type="Observation",
        entity_id=str(new_obs.id),
        previous_state={"status": prior_obs.status.value, "revision": prior_obs.revision},
        new_state={"status": "REJECTED", "revision": new_obs.revision},
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_obs)

    return ResponseEnvelope(
        success=True,
        message="Observation rejected and preserved in history",
        data=ObservationRead.model_validate(new_obs)
    )

@router.post(
    "/{inspection_id}/observations/{observation_id}/status",
    response_model=ResponseEnvelope[ObservationRead],
    summary="Update observation status (e.g. UNCERTAIN, CONFLICTING, UNKNOWN)",
)
async def update_observation_status(
    inspection_id: uuid.UUID,
    observation_id: uuid.UUID,
    payload: ObservationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)

    res = await db.execute(
        select(Observation).where(Observation.id == observation_id, Observation.inspection_id == inspection_id)
    )
    prior_obs = res.scalar_one_or_none()
    if not prior_obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target observation not found")

    if not prior_obs.is_latest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a superseded observation revision")

    new_obs = Observation(
        inspection_id=prior_obs.inspection_id,
        ocr_region_id=prior_obs.ocr_region_id,
        surface_id=prior_obs.surface_id,
        entity_run_id=prior_obs.entity_run_id,
        field_type=prior_obs.field_type,
        raw_value=prior_obs.raw_value,
        normalized_value=prior_obs.normalized_value,
        source=prior_obs.source,
        confidence=prior_obs.confidence,
        status=payload.status,
        bounding_box=prior_obs.bounding_box,
        evidence_reference=prior_obs.evidence_reference,
        package_dimensions=prior_obs.package_dimensions,
        pdp_dimensions=prior_obs.pdp_dimensions,
        character_height=prior_obs.character_height,
        calibration_info=prior_obs.calibration_info,
        measurement_uncertainty=prior_obs.measurement_uncertainty,
        revision=prior_obs.revision + 1,
        is_latest=True,
        revision_reason=payload.reason,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(new_obs)
    await db.flush()

    prior_obs.is_latest = False
    prior_obs.superseded_by_id = new_obs.id

    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="OBSERVATION_STATUS_UPDATED",
        entity_type="Observation",
        entity_id=str(new_obs.id),
        previous_state={"status": prior_obs.status.value, "revision": prior_obs.revision},
        new_state={"status": payload.status.value, "revision": new_obs.revision},
        justification=payload.reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_obs)

    return ResponseEnvelope(
        success=True,
        message=f"Observation status updated to {payload.status.value}",
        data=ObservationRead.model_validate(new_obs)
    )

# --------------------------------------------------------------------------
# 4. Adjudication History List
# --------------------------------------------------------------------------

@router.get(
    "/{inspection_id}/adjudications",
    response_model=ResponseEnvelope[List[OCRAdjudicationRead]],
    summary="List all OCR adjudication records for an inspection",
)
async def list_adjudications(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_inspection_or_404(inspection_id, db, current_user)

    res = await db.execute(
        select(OCRAdjudication)
        .where(OCRAdjudication.inspection_id == inspection_id)
        .order_by(OCRAdjudication.adjudicated_at.desc())
    )
    adjs = res.scalars().all()
    return ResponseEnvelope(
        success=True,
        data=[OCRAdjudicationRead.model_validate(a) for a in adjs]
    )

# --------------------------------------------------------------------------
# 5. Deterministic Rule Re-evaluation
# --------------------------------------------------------------------------

@router.post(
    "/{inspection_id}/rules/re-evaluate",
    response_model=ResponseEnvelope[RuleReevaluationResponse],
    summary="Re-evaluate deterministic legal rules following human adjudication",
)
async def reevaluate_inspection_rules(
    inspection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rule_engine: DeterministicRuleEngine = Depends(get_rule_engine_service),
):
    """
    Executes the authoritative backend deterministic rule engine.
    Frontend NEVER calculates legal compliance.
    Preserves all previous rule evaluations and produces a full delta comparison.
    """
    inspection = await _get_inspection_or_404(inspection_id, db, current_user)

    # 1. Fetch previous latest evaluation run to compute delta
    prev_run_id_res = await db.execute(
        select(RuleEvaluation.evaluation_run_id)
        .where(RuleEvaluation.inspection_id == inspection_id)
        .order_by(RuleEvaluation.evaluated_at.desc())
        .limit(1)
    )
    prev_run_id = prev_run_id_res.scalar_one_or_none()

    prev_evals_by_code: Dict[str, RuleEvaluation] = {}
    prev_verdict: Optional[RuleOutcome] = None
    if prev_run_id:
        prev_res = await db.execute(
            select(RuleEvaluation)
            .options(selectinload(RuleEvaluation.rule_definition))
            .where(RuleEvaluation.inspection_id == inspection_id, RuleEvaluation.evaluation_run_id == prev_run_id)
        )
        for pe in prev_res.scalars().all():
            r_code = pe.rule_code or (pe.rule_definition.rule_code if pe.rule_definition else "")
            prev_evals_by_code[r_code] = pe

        # Determine prior overall verdict
        if any(pe.outcome == RuleOutcome.FAIL for pe in prev_evals_by_code.values()):
            prev_verdict = RuleOutcome.FAIL
        elif any(pe.outcome == RuleOutcome.REVIEW for pe in prev_evals_by_code.values()):
            prev_verdict = RuleOutcome.REVIEW
        elif any(pe.outcome == RuleOutcome.PASS for pe in prev_evals_by_code.values()):
            prev_verdict = RuleOutcome.PASS
        else:
            prev_verdict = RuleOutcome.INDETERMINATE

    # 2. Execute authoritative deterministic rule engine
    summary = await rule_engine.evaluate_inspection(
        db=db,
        inspection=inspection,
        actor_id=current_user.id,
    )

    # 3. Load newly saved evaluations with rule definitions
    new_res = await db.execute(
        select(RuleEvaluation)
        .options(selectinload(RuleEvaluation.rule_definition))
        .where(RuleEvaluation.inspection_id == inspection_id, RuleEvaluation.evaluation_run_id == summary.evaluation_run_id)
        .order_by(RuleEvaluation.rule_definition_id.asc())
    )
    new_evals = new_res.scalars().all()

    # 4. Compute changes
    changes: List[RuleEvaluationChange] = []
    for ne in new_evals:
        r_code = ne.rule_code or (ne.rule_definition.rule_code if ne.rule_definition else "RULE")
        pe = prev_evals_by_code.get(r_code)
        prev_out = pe.outcome if pe else None
        changed = (prev_out != ne.outcome)

        changes.append(
            RuleEvaluationChange(
                rule_code=r_code,
                statutory_citation=ne.statutory_citation,
                previous_outcome=prev_out,
                new_outcome=ne.outcome,
                legal_rationale=ne.legal_rationale,
                outcome_changed=changed,
            )
        )

    # 5. Audit Log entry for re-evaluation
    audit = AuditLog(
        inspection_id=inspection_id,
        user_id=current_user.id,
        action="RULES_REEVALUATED",
        entity_type="RuleEvaluationRun",
        entity_id=str(summary.evaluation_run_id),
        previous_state={
            "previous_run_id": str(prev_run_id) if prev_run_id else None,
            "previous_verdict": prev_verdict.value if prev_verdict else None,
        },
        new_state={
            "new_run_id": str(summary.evaluation_run_id),
            "pass_count": summary.pass_count,
            "fail_count": summary.fail_count,
            "review_count": summary.review_count,
            "indeterminate_count": summary.indeterminate_count,
            "total_rules": summary.total_rules,
        },
        justification=f"Re-evaluated deterministic compliance rules following human adjudication. Outcome: {summary.pass_count} PASS, {summary.fail_count} FAIL, {summary.review_count} REVIEW.",
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    await db.commit()

    if summary.fail_count > 0:
        new_verdict = RuleOutcome.FAIL
    elif summary.review_count > 0:
        new_verdict = RuleOutcome.REVIEW
    elif summary.pass_count > 0:
        new_verdict = RuleOutcome.PASS
    elif summary.indeterminate_count > 0:
        new_verdict = RuleOutcome.INDETERMINATE
    else:
        new_verdict = RuleOutcome.NOT_APPLICABLE

    return ResponseEnvelope(
        success=True,
        message=(
            f"Rule re-evaluation complete: {summary.pass_count} PASS, {summary.fail_count} FAIL, "
            f"{summary.review_count} REVIEW. {sum(1 for c in changes if c.outcome_changed)} rule verdicts changed."
        ),
        data=RuleReevaluationResponse(
            inspection_id=inspection_id,
            previous_evaluation_run_id=prev_run_id,
            new_evaluation_run_id=summary.evaluation_run_id,
            evaluated_at=summary.evaluated_at,
            previous_verdict=prev_verdict,
            new_verdict=new_verdict,
            total_rules=summary.total_rules,
            pass_count=summary.pass_count,
            fail_count=summary.fail_count,
            review_count=summary.review_count,
            indeterminate_count=summary.indeterminate_count,
            not_applicable_count=summary.not_applicable_count,
            changes=changes,
            evaluations=[RuleEvaluationRead.model_validate(ne) for ne in new_evals],
        )
    )
