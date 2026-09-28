import uuid
import pytest
from datetime import datetime, timezone
from app.models.enums import SurfaceType, FieldType, ObservationStatus, RuleOutcome
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.services.evidence.service import EvidenceService
from app.services.evidence.bundle import EvidenceBundleBuilder
from app.services.evidence.integrity import (
    calculate_sha256,
    calculate_canonical_json_sha256,
    verify_canonical_json_sha256,
)

@pytest.mark.asyncio
async def test_canonical_json_integrity_hashing():
    """Verify deterministic JSON hashing regardless of key order."""
    dict_a = {"alpha": "1", "beta": 2, "gamma": [1, 2, 3]}
    dict_b = {"gamma": [1, 2, 3], "alpha": "1", "beta": 2}

    hash_a = calculate_canonical_json_sha256(dict_a)
    hash_b = calculate_canonical_json_sha256(dict_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64
    assert verify_canonical_json_sha256(dict_a, hash_a) is True
    assert verify_canonical_json_sha256(dict_a, "incorrect_hash") is False

@pytest.mark.asyncio
async def test_evidence_manifest_builder_and_hash():
    """Verify EvidenceBundleBuilder assembles valid manifest with SHA-256 integrity items."""
    insp_id = uuid.uuid4()
    surf_id = uuid.uuid4()
    ocr_id = uuid.uuid4()
    obs_id = uuid.uuid4()

    inspection = Inspection(
        id=insp_id,
        inspection_number="INSP-EV-TEST-001",
        retail_outlet_name="Test Mart",
        initiated_at=datetime.now(timezone.utc),
    )

    surface = InspectionSurface(
        id=surf_id,
        inspection_id=insp_id,
        surface_type=SurfaceType.FRONT_PDP,
        image_storage_path="inspections/test/original/front.jpg",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        image_width=1000,
        image_height=800,
        file_size_bytes=10240,
        captured_at=datetime.now(timezone.utc),
    )

    ocr_run = OCRRun(
        id=ocr_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        provider_name="Tesseract",
        provider_version="5.4.0",
        preprocessing_variant="contrast_enhanced",
        status="COMPLETED",
        total_regions_detected=1,
        executed_at=datetime.now(timezone.utc),
    )

    ocr_reg = OCRRegion(
        id=uuid.uuid4(),
        surface_id=surf_id,
        ocr_run_id=ocr_id,
        raw_text="NET QTY: 500 g",
        confidence=0.98,
        bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
    )
    ocr_run.regions = [ocr_reg]

    obs = Observation(
        id=obs_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        ocr_region_id=ocr_reg.id,
        field_type=FieldType.NET_QUANTITY,
        raw_value="NET QTY: 500 g",
        normalized_value={"value": 500, "unit": "g", "formatted": "500 g"},
        confidence=0.98,
        status=ObservationStatus.OBSERVED,
        revision=1,
        is_latest=True,
    )

    geom = PDPGeometry(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        surface_id=surf_id,
        surface_type=SurfaceType.FRONT_PDP,
        is_pdp_candidate=True,
        image_width=1000,
        image_height=800,
        pdp_pixel_area=800000.0,
        has_calibration=True,
        scale_px_per_mm=10.0,
        estimated_physical_area_sq_cm=80.0,
        status="COMPLETED",
        analyzed_at=datetime.now(timezone.utc),
    )

    rule_def = RuleDefinition(
        id=uuid.uuid4(),
        rule_code="PCR-2011-R06-1-C",
        title="Net Quantity Declaration",
        legal_act="Legal Metrology Act, 2009",
        rule_reference="Rule 6(1)(c)",
        version="1.0",
    )

    evaluation = RuleEvaluation(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        rule_definition_id=rule_def.id,
        rule_definition=rule_def,
        outcome=RuleOutcome.PASS,
        statutory_citation="PCMR 2011 Rule 6(1)(c)",
        legal_rationale="Statutory net quantity declaration verified: 500 g.",
        evidence_references={"observation_ids": [str(obs_id)], "source_region_ids": [str(ocr_reg.id)]},
        evaluated_at=datetime.now(timezone.utc),
    )

    audit = AuditLog(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        action="TEST_ACTION",
        entity_type="Inspection",
        entity_id=str(insp_id),
        justification="Unit test audit entry",
        performed_at=datetime.now(timezone.utc),
    )

    manifest = EvidenceBundleBuilder.build_manifest(
        inspection=inspection,
        surfaces=[surface],
        ocr_runs=[ocr_run],
        observations=[obs],
        geometries=[geom],
        evaluations=[evaluation],
        audit_logs=[audit],
    )

    assert manifest.inspection_id == str(insp_id)
    assert len(manifest.images) == 1
    assert manifest.images[0]["sha256_hash"] == surface.sha256_hash
    assert len(manifest.rule_evaluations) == 1
    assert manifest.rule_evaluations[0]["outcome"] == "PASS"
    assert len(manifest.integrity.items) == 1
    assert manifest.integrity.items[0].sha256_hash == surface.sha256_hash

@pytest.mark.asyncio
async def test_evidence_graph_backward_traceability():
    """Verify evidence graph traverses backward from RuleEvaluation to original image SHA-256."""
    insp_id = uuid.uuid4()
    surf_id = uuid.uuid4()
    ocr_id = uuid.uuid4()
    reg_id = uuid.uuid4()
    obs_id = uuid.uuid4()
    eval_id = uuid.uuid4()

    surface = InspectionSurface(
        id=surf_id,
        inspection_id=insp_id,
        surface_type=SurfaceType.FRONT_PDP,
        image_storage_path="inspections/test/original/front.jpg",
        sha256_hash="abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
    )

    ocr_reg = OCRRegion(
        id=reg_id,
        surface_id=surf_id,
        ocr_run_id=ocr_id,
        raw_text="500 g",
        confidence=0.99,
        bounding_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.05},
    )

    ocr_run = OCRRun(
        id=ocr_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        provider_name="Tesseract",
        status="COMPLETED",
    )
    ocr_run.regions = [ocr_reg]

    obs = Observation(
        id=obs_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        ocr_region_id=reg_id,
        field_type=FieldType.NET_QUANTITY,
        raw_value="500 g",
        confidence=0.99,
        status=ObservationStatus.OBSERVED,
        is_latest=True,
    )

    rule_def = RuleDefinition(
        id=uuid.uuid4(),
        rule_code="PCR-2011-R06-1-C",
        title="Net Quantity",
    )

    evaluation = RuleEvaluation(
        id=eval_id,
        inspection_id=insp_id,
        rule_definition=rule_def,
        outcome=RuleOutcome.PASS,
        statutory_citation="Rule 6(1)(c)",
        legal_rationale="Pass",
        evidence_references={"observation_ids": [str(obs_id)], "source_region_ids": [str(reg_id)]},
    )

    service = EvidenceService()
    graph = service.build_evidence_graph(
        surfaces=[surface],
        ocr_runs=[ocr_run],
        observations=[obs],
        geometries=[],
        evaluations=[evaluation],
    )

    assert str(eval_id) in graph.nodes
    assert str(obs_id) in graph.nodes
    assert str(reg_id) in graph.nodes
    assert str(surf_id) in graph.nodes

    # Trace backward lineage from RuleEvaluation
    lineage = graph.trace_lineage(str(eval_id))
    lineage_node_ids = {n.node_id for n in lineage}

    assert str(eval_id) in lineage_node_ids
    assert str(obs_id) in lineage_node_ids
    assert str(reg_id) in lineage_node_ids
    assert str(ocr_id) in lineage_node_ids
    assert str(surf_id) in lineage_node_ids

    # Find the surface node in lineage and verify original image SHA-256 hash preservation
    surf_nodes = [n for n in lineage if n.node_id == str(surf_id)]
    assert len(surf_nodes) == 1
    assert surf_nodes[0].properties["sha256_hash"] == surface.sha256_hash

@pytest.mark.asyncio
async def test_evidence_reference_validation():
    """Verify validation detects valid and orphan evidence references."""
    obs_id = uuid.uuid4()
    reg_id = uuid.uuid4()
    surf_id = uuid.uuid4()

    obs = Observation(id=obs_id, field_type=FieldType.NET_QUANTITY, raw_value="100g")
    ocr_reg = OCRRegion(id=reg_id, raw_text="100g")
    surface = InspectionSurface(id=surf_id, surface_type=SurfaceType.FRONT_PDP, image_storage_path="p", sha256_hash="h")

    # Evaluation with valid references
    eval_valid = RuleEvaluation(
        id=uuid.uuid4(),
        evidence_references={"observation_ids": [str(obs_id)], "source_region_ids": [str(reg_id)]},
    )

    service = EvidenceService()
    res_valid = service.validate_evidence_references(
        evaluations=[eval_valid],
        observations=[obs],
        ocr_regions=[ocr_reg],
        surfaces=[surface],
    )
    assert res_valid["is_valid"] is True
    assert len(res_valid["missing_references"]) == 0

    # Evaluation with missing/orphan references
    orphan_id = str(uuid.uuid4())
    eval_invalid = RuleEvaluation(
        id=uuid.uuid4(),
        evidence_references={"observation_ids": [orphan_id], "source_region_ids": [str(reg_id)]},
    )
    res_invalid = service.validate_evidence_references(
        evaluations=[eval_invalid],
        observations=[obs],
        ocr_regions=[ocr_reg],
        surfaces=[surface],
    )
    assert res_invalid["is_valid"] is False
    assert len(res_invalid["missing_references"]) == 1
    assert res_invalid["missing_references"][0]["id"] == orphan_id
