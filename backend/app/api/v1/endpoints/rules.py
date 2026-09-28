import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.inspection import Inspection
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.rule import (
    RuleDefinitionCreate,
    RuleDefinitionRead,
    RuleEvaluationCreate,
    RuleEvaluationOverride,
    RuleEvaluationRead,
)
from app.schemas.common import ResponseEnvelope
from app.api.deps import get_current_user, require_roles
from app.services.rules.registry import RuleRegistry

router = APIRouter()

async def _list_rules(
    active_only: bool,
    jurisdiction: Optional[str],
    category: Optional[str],
    include_test_rules: bool,
    db: AsyncSession,
) -> List[RuleDefinition]:
    # Ensure authoritative rules are seeded
    await RuleRegistry.seed_rules(db, include_test_rules=include_test_rules)

    query = select(RuleDefinition)
    if active_only:
        query = query.where(RuleDefinition.is_active == True)
    if not include_test_rules:
        query = query.where(RuleDefinition.is_test_rule == False)
    if jurisdiction:
        query = query.where(RuleDefinition.jurisdiction == jurisdiction)
    if category:
        query = query.where(RuleDefinition.category == category)

    result = await db.execute(query.order_by(RuleDefinition.rule_code.asc(), RuleDefinition.version.desc()))
    return list(result.scalars().all())

@router.get("", response_model=ResponseEnvelope[List[RuleDefinitionRead]], summary="List all legal rule definitions")
@router.get("/definitions", response_model=ResponseEnvelope[List[RuleDefinitionRead]], summary="List all legal rule definitions (alias)")
async def list_rule_definitions(
    active_only: bool = Query(True),
    jurisdiction: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    include_test_rules: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List versioned Legal Metrology rule definitions.
    Rules are declarative and stored in the database, not hardcoded in application code.
    """
    definitions = await _list_rules(active_only, jurisdiction, category, include_test_rules, db)
    return ResponseEnvelope(
        success=True,
        data=[RuleDefinitionRead.model_validate(d) for d in definitions]
    )

@router.post("/definitions", response_model=ResponseEnvelope[RuleDefinitionRead], status_code=status.HTTP_201_CREATED)
async def create_rule_definition(
    rule_in: RuleDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ADJUDICATOR])),
):
    """
    Register a new versioned Legal Metrology rule definition.
    Allows amendments to be imported without rewriting application code.
    """
    existing = await db.execute(
        select(RuleDefinition).where(
            RuleDefinition.rule_code == rule_in.rule_code,
            RuleDefinition.version == rule_in.version,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule {rule_in.rule_code} version {rule_in.version} already exists"
        )
    
    rule_def = RuleDefinition(**rule_in.model_dump())
    db.add(rule_def)
    await db.commit()
    await db.refresh(rule_def)
    return ResponseEnvelope(
        success=True,
        message="Versioned rule definition registered",
        data=RuleDefinitionRead.model_validate(rule_def)
    )

@router.get("/definitions/{rule_code}", response_model=ResponseEnvelope[List[RuleDefinitionRead]], summary="Get versions of rule by code (alias)")
@router.get("/{rule_code}", response_model=ResponseEnvelope[List[RuleDefinitionRead]], summary="Get versions of rule by code")
async def get_rule_versions(
    rule_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all historical and active versions of a specific rule code."""
    # Ensure seed rules exist
    await RuleRegistry.seed_rules(db, include_test_rules=True)

    result = await db.execute(
        select(RuleDefinition)
        .where(RuleDefinition.rule_code == rule_code)
        .order_by(RuleDefinition.version.desc())
    )
    versions = result.scalars().all()
    if not versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule code not found")
    return ResponseEnvelope(
        success=True,
        data=[RuleDefinitionRead.model_validate(v) for v in versions]
    )

@router.post("/evaluations", response_model=ResponseEnvelope[RuleEvaluationRead], status_code=status.HTTP_201_CREATED)
async def record_rule_evaluation(
    eval_in: RuleEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record an independent rule evaluation verdict from the deterministic Rule Engine.
    Outcomes supported: PASS, FAIL, REVIEW, INDETERMINATE, NOT_APPLICABLE.
    Traceable to rule, observations, bounding boxes, and statutory citations.
    """
    ins = await db.execute(select(Inspection).where(Inspection.id == eval_in.inspection_id))
    if not ins.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    r_def = await db.execute(select(RuleDefinition).where(RuleDefinition.id == eval_in.rule_definition_id))
    rule_def = r_def.scalar_one_or_none()
    if not rule_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule definition not found")

    eval_data = eval_in.model_dump()
    eval_data.pop("rule_code", None)
    if not eval_data.get("rule_version"):
        eval_data["rule_version"] = rule_def.version

    rule_eval = RuleEvaluation(
        **eval_data,
        evaluated_at=datetime.now(timezone.utc)
    )
    db.add(rule_eval)
    await db.commit()
    await db.refresh(rule_eval)
    return ResponseEnvelope(
        success=True,
        message="Rule evaluation recorded",
        data=RuleEvaluationRead.model_validate(rule_eval)
    )

@router.post("/evaluations/{evaluation_id}/override", response_model=ResponseEnvelope[RuleEvaluationRead])
async def override_rule_evaluation(
    evaluation_id: uuid.UUID,
    override_in: RuleEvaluationOverride,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADJUDICATOR, UserRole.ADMIN])),
):
    """
    Adjudicate and override a rule evaluation outcome.
    Requires mandatory justification and records to the immutable AuditLog.
    """
    res = await db.execute(select(RuleEvaluation).where(RuleEvaluation.id == evaluation_id))
    rule_eval = res.scalar_one_or_none()
    if not rule_eval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule evaluation not found")

    prev_outcome = rule_eval.outcome.value

    rule_eval.outcome = override_in.outcome
    rule_eval.officer_overridden = True
    rule_eval.override_reason = override_in.override_reason
    rule_eval.overriding_officer_id = current_user.id

    # Append to Audit Log
    audit = AuditLog(
        id=uuid.uuid4(),
        inspection_id=rule_eval.inspection_id,
        user_id=current_user.id,
        action="RULE_EVALUATION_OVERRIDDEN",
        entity_type="RuleEvaluation",
        entity_id=str(rule_eval.id),
        previous_state={"outcome": prev_outcome},
        new_state={"outcome": override_in.outcome.value},
        justification=override_in.override_reason,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rule_eval)

    return ResponseEnvelope(
        success=True,
        message=f"Rule evaluation overridden to {override_in.outcome.value}",
        data=RuleEvaluationRead.model_validate(rule_eval)
    )
