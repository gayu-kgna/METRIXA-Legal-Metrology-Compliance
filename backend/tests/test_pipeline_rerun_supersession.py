import uuid
import hashlib
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.observation import Observation
from app.models.entity_run import EntityParsingRun
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.enums import FieldType, ObservationStatus, ObservationSource, RuleOutcome, InspectionOverallStatus
from app.services.entity.normalizer import EntityNormalizer
from app.services.entity.classifiers import EntityClassifier
from app.services.entity.parser import EntityParsingService
from app.services.rules.engine import DeterministicRuleEngine
from app.services.rules.evaluators import DeterministicEvaluator
from app.services.rules.models import EvaluationContext, ApplicabilityResult
from app.services.evidence.service import EvidenceService


# =============================================================================
# Requirement 10: Regression Tests A through L
# =============================================================================

# -----------------------------------------------------------------------------
# Test K: Multipack 10 packs of 71g Normalization
# -----------------------------------------------------------------------------
def test_multipack_10_packs_71g_normalization():
    """
    Requirement 8 & 10.K:
    Normalize '10 packs of 71g' preserving count, individual quantity/unit,
    total quantity/unit, and canonical magnitude.
    """
    normalizer = EntityNormalizer()
    raw_str = "10 packs of 71g"
    norm = normalizer.normalize_quantity(raw_str)

    assert norm is not None, "Multipack string must be successfully parsed"
    assert norm.count == 10, f"Expected count=10, got {norm.count}"
    assert norm.individual_quantity == 71.0, f"Expected individual_quantity=71.0, got {norm.individual_quantity}"
    assert norm.individual_unit == "g", f"Expected individual_unit='g', got {norm.individual_unit}"
    assert norm.total_quantity == 710.0, f"Expected total_quantity=710.0, got {norm.total_quantity}"
    assert norm.total_unit == "g", f"Expected total_unit='g', got {norm.total_unit}"
    assert norm.value == 710.0, f"Canonical value must be total quantity 710.0, got {norm.value}"
    assert norm.unit == "g"
    assert norm.raw_declaration == raw_str


# -----------------------------------------------------------------------------
# Test L: Marketed By Remains MARKETED_BY
# -----------------------------------------------------------------------------
def test_marketed_by_role_semantics():
    """
    Requirement 9 & 10.L:
    Verify that 'Marketed By: BRITANNIA INDUSTRIES LTD.' preserves
    entity_type = 'MARKETED_BY' and is NOT automatically changed to MANUFACTURER.
    """
    classifier = EntityClassifier()
    regions = [
        OCRRegion(
            id=uuid.uuid4(),
            surface_id=uuid.uuid4(),
            raw_text="Marketed By: BRITANNIA INDUSTRIES LTD., 5/1A HUNGERFORD STREET, KOLKATA",
            confidence=0.98,
            bounding_box={"ymin": 0.2, "xmin": 0.1, "ymax": 0.3, "xmax": 0.9},
            token_order=1,
        )
    ]
    parsed = classifier.classify_and_parse(regions, regions[0].raw_text)

    # Find party observation
    party_entities = [p for p in parsed if p.field_type == FieldType.MANUFACTURER_NAME]
    assert len(party_entities) >= 1, "Should extract party entity"
    party = party_entities[0]
    norm = party.normalized_value or {}
    assert norm.get("entity_type") == "MARKETED_BY", (
        f"Expected entity_type='MARKETED_BY', got {norm.get('entity_type')}"
    )


# -----------------------------------------------------------------------------
# Test I: Missing MRP Does Not Automatically Become Confirmed Absence
# -----------------------------------------------------------------------------
def test_missing_mrp_does_not_become_confirmed_absence():
    """
    Requirement 7 & 10.I:
    When MRP is not found on partial OCR evidence and not single-surface
    comprehensive label, rule must return INDETERMINATE, not FAIL.
    """
    rule = RuleDefinition(
        id=uuid.uuid4(),
        rule_code="LMR_R6_1_DA_MRP_PRESENCE",
        version="1.0.0",
        legal_act="Legal Metrology Act, 2009",
        rule_reference="Rule 6(1)(da)",
        title="Maximum Retail Price Declaration",
        description="MRP must be declared",
        parameters={},
        evaluation_logic={"type": "MRP_DECLARATION"},
        evidence_requirements={"required_fields": ["MRP"]},
        severity="MANDATORY",
        is_active=True,
    )
    # Inspection with 1 surface (FRONT_PDP only, no BACK, not comprehensive)
    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=uuid.uuid4(),
        surface_type="FRONT_PDP",
        image_storage_path="mock.jpg",
        sha256_hash="abc",
        file_size_bytes=100,
    )
    context = EvaluationContext(
        inspection=Inspection(id=surface.inspection_id, inspection_number="TEST-001"),
        product=None,
        observations_by_type={},  # No MRP observation
        surfaces=[surface],
        pdp_geometries=[],
        evaluation_timestamp=datetime.now(timezone.utc),
    )
    applicability = ApplicabilityResult(is_applicable=True, reason="Applicable to all pre-packaged commodities")

    result = DeterministicEvaluator.evaluate(rule, context, applicability)
    assert result.outcome == RuleOutcome.INDETERMINATE, (
        f"Expected INDETERMINATE for missing OCR MRP, got {result.outcome}"
    )
    assert "not confidently observable" in result.legal_rationale.lower() or "not observable" in result.legal_rationale.lower()


# -----------------------------------------------------------------------------
# Test J: Missing MFG_DATE Does Not Automatically Become Confirmed Absence
# -----------------------------------------------------------------------------
def test_missing_mfg_date_does_not_become_confirmed_absence():
    """
    Requirement 7 & 10.J:
    When MFG/Packing Date is not found on partial OCR evidence,
    rule must return INDETERMINATE, not FAIL.
    """
    rule = RuleDefinition(
        id=uuid.uuid4(),
        rule_code="LMR_R6_1_D_DATE_PRESENCE",
        version="1.0.0",
        legal_act="Legal Metrology Act, 2009",
        rule_reference="Rule 6(1)(d)",
        title="Date of Manufacture or Packing Declaration",
        description="Date must be declared",
        parameters={},
        evaluation_logic={"type": "DATE_DECLARATION"},
        evidence_requirements={"required_fields": ["MFG_DATE"]},
        severity="MANDATORY",
        is_active=True,
    )
    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=uuid.uuid4(),
        surface_type="FRONT_PDP",
        image_storage_path="mock.jpg",
        sha256_hash="abc",
        file_size_bytes=100,
    )
    context = EvaluationContext(
        inspection=Inspection(id=surface.inspection_id, inspection_number="TEST-002"),
        product=None,
        observations_by_type={},  # No Date observation
        surfaces=[surface],
        pdp_geometries=[],
        evaluation_timestamp=datetime.now(timezone.utc),
    )
    applicability = ApplicabilityResult(is_applicable=True, reason="Applicable")

    result = DeterministicEvaluator.evaluate(rule, context, applicability)
    assert result.outcome == RuleOutcome.INDETERMINATE, (
        f"Expected INDETERMINATE for missing OCR MFG_DATE, got {result.outcome}"
    )


# -----------------------------------------------------------------------------
# Tests A, B, C, D, E, F: Entity Parse Repeated Runs & Supersession Integrity
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_entity_parse_repeated_runs_and_supersession_integrity(
    db_session: AsyncSession,
    test_inspector,
):
    """
    Requirements 1, 2 & 10.A, 10.B, 10.C, 10.D, 10.E, 10.F:
    A. First entity parse on clean inspection
    B. Second entity parse on same inspection (must not trigger ForeignKeyViolationError!)
    C. Third entity parse on same inspection
    D. Valid superseded_by foreign keys pointing to real rows
    E. Exactly one latest observation per logical declaration
    F. No orphan superseded_by_id references
    """
    # 1. Setup clean Inspection, Surface, and OCRRun
    inspection = Inspection(
        id=uuid.uuid4(),
        inspection_number=f"TEST-RERUN-{uuid.uuid4().hex[:6].upper()}",
        inspector_id=test_inspector.id,
        overall_status=InspectionOverallStatus.PENDING,
    )
    db_session.add(inspection)
    await db_session.flush()

    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=inspection.id,
        surface_type="FRONT_PDP",
        image_storage_path="storage/test_pdp.jpg",
        sha256_hash=hashlib.sha256(b"test_img").hexdigest(),
        image_width=1000,
        image_height=800,
        file_size_bytes=1024,
    )
    db_session.add(surface)
    await db_session.flush()

    ocr_run = OCRRun(
        id=uuid.uuid4(),
        surface_id=surface.id,
        inspection_id=inspection.id,
        provider_name="TESSERACT_OCR",
        status="COMPLETED",
        total_regions_detected=2,
        metadata_json={
            "raw_text": "Net Qty: 500 g\nMarketed By: BRITANNIA INDUSTRIES LTD."
        },
    )
    db_session.add(ocr_run)
    await db_session.flush()

    region1 = OCRRegion(
        id=uuid.uuid4(),
        ocr_run_id=ocr_run.id,
        surface_id=surface.id,
        raw_text="Net Qty: 500 g",
        confidence=0.98,
        bounding_box={"ymin": 0.8, "xmin": 0.2, "ymax": 0.85, "xmax": 0.4},
        token_order=1,
    )
    region2 = OCRRegion(
        id=uuid.uuid4(),
        ocr_run_id=ocr_run.id,
        surface_id=surface.id,
        raw_text="Marketed By: BRITANNIA INDUSTRIES LTD.",
        confidence=0.97,
        bounding_box={"ymin": 0.6, "xmin": 0.1, "ymax": 0.65, "xmax": 0.7},
        token_order=2,
    )
    db_session.add_all([region1, region2])
    await db_session.commit()

    parser_service = EntityParsingService()

    # --- RUN 1 (Requirement 10.A): First entity parse on clean inspection ---
    run1 = await parser_service.execute_entity_pipeline(
        db=db_session,
        inspection=inspection,
        surface=surface,
        ocr_run_id=ocr_run.id,
    )
    assert run1.status == "COMPLETED"

    # Verify Run 1 observations
    obs1_res = await db_session.execute(
        select(Observation).where(Observation.inspection_id == inspection.id)
    )
    obs1_list = list(obs1_res.scalars().all())
    assert len(obs1_list) >= 2, "Run 1 must create at least 2 observations"
    for o in obs1_list:
        assert o.is_latest is True, "Run 1 observations must all have is_latest=True"
        assert o.superseded_by_id is None, "Run 1 observations must not be superseded"
        assert o.revision == 1, "Run 1 observations must have revision=1"

    # --- RUN 2 (Requirement 10.B): Second entity parse on same inspection ---
    # MUST NOT raise ForeignKeyViolationError (Root cause fix validation!)
    run2 = await parser_service.execute_entity_pipeline(
        db=db_session,
        inspection=inspection,
        surface=surface,
        ocr_run_id=ocr_run.id,
    )
    assert run2.status == "COMPLETED"

    # Verify Run 2 observations & supersession (Requirement 10.D, 10.E, 10.F)
    obs2_res = await db_session.execute(
        select(Observation).where(Observation.inspection_id == inspection.id)
    )
    all_obs_after_run2 = list(obs2_res.scalars().all())

    latest_obs_run2 = [o for o in all_obs_after_run2 if o.is_latest]
    superseded_obs_run2 = [o for o in all_obs_after_run2 if not o.is_latest]

    # Requirement 10.E: Exactly one latest observation per logical declaration
    latest_types = [o.field_type for o in latest_obs_run2]
    assert len(latest_types) == len(set(latest_types)), (
        f"Duplicate latest observations found: {latest_types}"
    )

    # Requirement 10.D: Valid superseded_by foreign keys
    all_obs_ids = {o.id for o in all_obs_after_run2}
    for old_obs in superseded_obs_run2:
        assert old_obs.superseded_by_id is not None, "Old observation must have superseded_by_id set"
        # Requirement 10.F: No orphan superseded_by_id
        assert old_obs.superseded_by_id in all_obs_ids, (
            f"superseded_by_id {old_obs.superseded_by_id} must reference a valid existing observation"
        )
        assert old_obs.revision == 1

    for new_obs in latest_obs_run2:
        assert new_obs.revision == 2, "New observations in Run 2 must have revision=2"
        assert new_obs.superseded_by_id is None

    # --- RUN 3 (Requirement 10.C): Third entity parse on same inspection ---
    run3 = await parser_service.execute_entity_pipeline(
        db=db_session,
        inspection=inspection,
        surface=surface,
        ocr_run_id=ocr_run.id,
    )
    assert run3.status == "COMPLETED"

    obs3_res = await db_session.execute(
        select(Observation).where(Observation.inspection_id == inspection.id)
    )
    all_obs_after_run3 = list(obs3_res.scalars().all())

    latest_obs_run3 = [o for o in all_obs_after_run3 if o.is_latest]
    superseded_obs_run3 = [o for o in all_obs_after_run3 if not o.is_latest]

    # Requirement 10.E: Exactly one latest observation per logical declaration
    latest_types_3 = [o.field_type for o in latest_obs_run3]
    assert len(latest_types_3) == len(set(latest_types_3)), (
        f"Duplicate latest observations after Run 3: {latest_types_3}"
    )
    for new_obs in latest_obs_run3:
        assert new_obs.revision == 3, f"Run 3 latest observation must have revision=3, got {new_obs.revision}"

    # Requirement 10.D & 10.F: Check entire supersession chain validity
    all_ids_3 = {o.id for o in all_obs_after_run3}
    for old_obs in superseded_obs_run3:
        assert old_obs.superseded_by_id in all_ids_3, (
            f"Orphan superseded_by_id found: {old_obs.superseded_by_id}"
        )


# -----------------------------------------------------------------------------
# Test G: Failed Entity Parsing Prevents Rules / PDF
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_entity_parsing_prevents_rules_and_pdf(
    db_session: AsyncSession,
    test_inspector,
):
    """
    Requirement 4 & 10.G:
    If an entity parsing run has status FAILED, the rule engine must halt
    and refuse to execute with stale or incomplete observations.
    """
    inspection = Inspection(
        id=uuid.uuid4(),
        inspection_number=f"TEST-FAIL-{uuid.uuid4().hex[:6].upper()}",
        inspector_id=test_inspector.id,
        overall_status=InspectionOverallStatus.PENDING,
    )
    db_session.add(inspection)
    await db_session.flush()

    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=inspection.id,
        surface_type="FRONT_PDP",
        image_storage_path="storage/fail_test.jpg",
        sha256_hash="fakehash",
        file_size_bytes=500,
    )
    db_session.add(surface)
    await db_session.flush()

    ocr_run = OCRRun(
        id=uuid.uuid4(),
        surface_id=surface.id,
        inspection_id=inspection.id,
        provider_name="TESSERACT_OCR",
        status="COMPLETED",
    )
    db_session.add(ocr_run)
    await db_session.flush()

    # Mark a FAILED entity parsing run
    failed_entity_run = EntityParsingRun(
        id=uuid.uuid4(),
        inspection_id=inspection.id,
        surface_id=surface.id,
        ocr_run_id=ocr_run.id,
        status="FAILED",
        error_message="Simulated parser failure",
    )
    db_session.add(failed_entity_run)
    await db_session.commit()

    rule_engine = DeterministicRuleEngine()
    with pytest.raises(ValueError, match="entity parsing runs failed"):
        await rule_engine.evaluate_inspection(
            db=db_session,
            inspection=inspection,
            actor_id=test_inspector.id,
        )


# -----------------------------------------------------------------------------
# Test H: Repeated Rule Execution Does Not Mix Current and Historical Runs
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_repeated_rule_execution_isolates_runs(
    db_session: AsyncSession,
    client: AsyncClient,
    test_inspector,
    auth_headers: dict,
):
    """
    Requirement 3, 5 & 10.H:
    Repeated rule execution creates distinct evaluation_run_ids.
    Querying current evaluations or generating reports must NOT combine
    runs (e.g. must return 9 evaluations, not 18).
    """
    inspection = Inspection(
        id=uuid.uuid4(),
        inspection_number=f"TEST-MULTI-EVAL-{uuid.uuid4().hex[:6].upper()}",
        inspector_id=test_inspector.id,
        overall_status=InspectionOverallStatus.PENDING,
    )
    db_session.add(inspection)
    await db_session.flush()

    surface = InspectionSurface(
        id=uuid.uuid4(),
        inspection_id=inspection.id,
        surface_type="FRONT_PDP",
        image_storage_path="storage/multi_eval.jpg",
        sha256_hash="fakehash123",
        file_size_bytes=500,
    )
    db_session.add(surface)
    await db_session.flush()

    # Create 9 active rule definitions if they don't exist
    rule_engine = DeterministicRuleEngine()

    # Run 1: Evaluate inspection rules
    summary1 = await rule_engine.evaluate_inspection(
        db=db_session,
        inspection=inspection,
        actor_id=test_inspector.id,
    )
    run1_id = summary1.evaluation_run_id

    # Run 2: Re-evaluate inspection rules
    summary2 = await rule_engine.evaluate_inspection(
        db=db_session,
        inspection=inspection,
        actor_id=test_inspector.id,
    )
    run2_id = summary2.evaluation_run_id

    assert run1_id != run2_id, "Each execution must have a distinct evaluation_run_id"

    # Total evaluations in DB should be sum of both runs
    total_evals_res = await db_session.execute(
        select(RuleEvaluation).where(RuleEvaluation.inspection_id == inspection.id)
    )
    total_evals = list(total_evals_res.scalars().all())
    expected_per_run = len(summary1.evaluations)
    assert len(total_evals) == expected_per_run * 2, (
        f"DB should contain {expected_per_run * 2} historical evaluations"
    )

    # API call: GET /inspections/{id}/rules/evaluations?latest_only=true
    # MUST return only the latest run (expected_per_run), NOT 2x!
    resp = await client.get(
        f"/api/v1/inspections/{inspection.id}/rules/evaluations?latest_only=true",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    returned_evals = resp.json()["data"]
    assert len(returned_evals) == expected_per_run, (
        f"API must return only latest run ({expected_per_run} evaluations), got {len(returned_evals)}"
    )

    # Verify that all returned evaluations belong to run2
    for e in returned_evals:
        assert e["evaluation_run_id"] == str(run2_id), (
            f"Returned evaluation belongs to wrong run: {e['evaluation_run_id']} != {run2_id}"
        )

    # Dataset loader for PDF dossier: must load only latest run
    evidence_svc = EvidenceService()
    _, _, _, _, _, loaded_evals, _ = await evidence_svc.load_inspection_dataset(
        db=db_session,
        inspection_id=inspection.id,
        evaluation_run_id=None,  # auto-resolves to latest
    )
    assert len(loaded_evals) == expected_per_run, (
        f"Evidence dataset must resolve to latest run ({expected_per_run} evals), got {len(loaded_evals)}"
    )
