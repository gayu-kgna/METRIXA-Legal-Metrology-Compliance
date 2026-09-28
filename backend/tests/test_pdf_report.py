import io
import uuid
import pytest
from datetime import datetime, timezone
from pypdf import PdfReader

from app.models.enums import SurfaceType, FieldType, ObservationStatus, RuleOutcome, InspectionOverallStatus
from app.models.inspection import Inspection
from app.models.product import Product
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.models.evidence import EvidenceSnapshot
from app.services.report.pdf_generator import DossierPDFGenerator
from app.services.report.models import DossierOptions
from app.services.evidence.integrity import calculate_sha256

@pytest.mark.asyncio
async def test_pdf_dossier_generator_and_content_verification():
    """Verify DossierPDFGenerator builds valid PDF and programmatically verify text with pypdf."""
    insp_id = uuid.uuid4()
    surf_id = uuid.uuid4()
    ocr_id = uuid.uuid4()
    obs_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    product = Product(
        id=uuid.uuid4(),
        brand_name="Metrixa Foods",
        product_name="Atta Whole Wheat",
        gtin_barcode="8901234567890",
        category="Food Grains",
    )

    inspection = Inspection(
        id=insp_id,
        inspection_number="INSP-2026-PDF-001",
        retail_outlet_name="Metro Cash & Carry",
        retail_outlet_address="Outer Ring Road, Bengaluru",
        overall_status=InspectionOverallStatus.NON_COMPLIANT,
        product=product,
        initiated_at=datetime.now(timezone.utc),
    )

    surface = InspectionSurface(
        id=surf_id,
        inspection_id=insp_id,
        surface_type=SurfaceType.FRONT_PDP,
        image_storage_path="inspections/test/original/front.jpg",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        image_width=1200,
        image_height=900,
        file_size_bytes=45000,
        captured_at=datetime.now(timezone.utc),
    )

    ocr_run = OCRRun(
        id=ocr_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        provider_name="Tesseract",
        provider_version="5.4.0",
        preprocessing_variant="deskewed_contrast",
        status="COMPLETED",
        total_regions_detected=2,
        total_duration_ms=45.2,
        executed_at=datetime.now(timezone.utc),
    )

    ocr_reg1 = OCRRegion(
        id=uuid.uuid4(),
        surface_id=surf_id,
        ocr_run_id=ocr_id,
        raw_text="NET QTY: 1 kg",
        confidence=0.97,
        bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
    )
    ocr_reg2 = OCRRegion(
        id=uuid.uuid4(),
        surface_id=surf_id,
        ocr_run_id=ocr_id,
        raw_text="MRP Rs 60.00",
        confidence=0.95,
        bounding_box={"x": 0.1, "y": 0.3, "width": 0.3, "height": 0.05},
    )
    ocr_run.regions = [ocr_reg1, ocr_reg2]

    obs1 = Observation(
        id=obs_id,
        inspection_id=insp_id,
        surface_id=surf_id,
        ocr_region_id=ocr_reg1.id,
        field_type=FieldType.NET_QUANTITY,
        raw_value="NET QTY: 1 kg",
        normalized_value={"value": 1, "unit": "kg", "formatted": "1 kg"},
        confidence=0.97,
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
        image_width=1200,
        image_height=900,
        pdp_pixel_area=1080000.0,
        has_calibration=True,
        scale_px_per_mm=10.0,
        estimated_physical_area_sq_cm=108.0,
        status="COMPLETED",
        analyzed_at=datetime.now(timezone.utc),
    )

    rule1 = RuleDefinition(id=uuid.uuid4(), rule_code="PCR-2011-R06-1-C", title="Net Quantity", version="1.0")
    rule2 = RuleDefinition(id=uuid.uuid4(), rule_code="PCR-2011-R06-1-DA", title="MRP Declaration", version="1.0")
    rule3 = RuleDefinition(id=uuid.uuid4(), rule_code="PCR-2011-R09-1-PDP", title="Font Height", version="1.0")

    eval1 = RuleEvaluation(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        rule_definition=rule1,
        outcome=RuleOutcome.PASS,
        statutory_citation="PCMR 2011 Rule 6(1)(c)",
        legal_rationale="Net quantity declaration verified: 1 kg.",
        evidence_references={"observation_ids": [str(obs_id)], "source_region_ids": [str(ocr_reg1.id)]},
        evaluated_at=datetime.now(timezone.utc),
    )
    eval2 = RuleEvaluation(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        rule_definition=rule2,
        outcome=RuleOutcome.FAIL,
        statutory_citation="PCMR 2011 Rule 6(1)(da)",
        legal_rationale="MRP declaration missing mandatory 'inclusive of all taxes' clause.",
        evidence_references={"observation_ids": [], "source_region_ids": []},
        evaluated_at=datetime.now(timezone.utc),
    )
    eval3 = RuleEvaluation(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        rule_definition=rule3,
        outcome=RuleOutcome.REVIEW,
        statutory_citation="PCMR 2011 Rule 9(1)",
        legal_rationale="Font height requires officer manual measurement verification.",
        evidence_references={"observation_ids": [], "source_region_ids": []},
        evaluated_at=datetime.now(timezone.utc),
    )

    audit = AuditLog(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        action="INSPECTION_INITIATED",
        entity_type="Inspection",
        entity_id=str(insp_id),
        justification="Initial inspection creation",
        performed_at=datetime.now(timezone.utc),
    )

    snapshot = EvidenceSnapshot(
        id=snap_id,
        inspection_id=insp_id,
        application_version="1.0.0",
        integrity_hash="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
    )

    generator = DossierPDFGenerator(storage_service=None)
    result = await generator.generate_dossier(
        inspection=inspection,
        surfaces=[surface],
        ocr_runs=[ocr_run],
        observations=[obs1],
        geometries=[geom],
        evaluations=[eval1, eval2, eval3],
        audit_logs=[audit],
        snapshot=snapshot,
        report_version=1,
        options=DossierOptions(include_images=False),  # Text & table test
    )

    assert result.pdf_bytes is not None
    assert len(result.pdf_bytes) > 0
    assert result.sha256_hash == calculate_sha256(result.pdf_bytes)

    # Programmatic PDF text verification with pypdf
    reader = PdfReader(io.BytesIO(result.pdf_bytes))
    assert len(reader.pages) >= 1

    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""
    full_text_norm = " ".join(full_text.split())

    # Required Brand & Sections
    assert "METRIXA" in full_text_norm
    assert "Legal Metrology Inspection Dossier" in full_text_norm
    assert "LEGAL & EVIDENTIARY DISCLAIMER" in full_text_norm
    assert "not a government-issued certificate" in full_text_norm
    assert "1. Inspection Metadata" in full_text_norm
    assert "2. Product Information" in full_text_norm
    assert "3. Package Surface Overview" in full_text_norm
    assert "5. Modular OCR Evidence" in full_text_norm
    assert "6. Extracted Statutory Declarations" in full_text_norm
    assert "7. Principal Display Panel (PDP) Geometry Measurements" in full_text_norm
    assert "8. Legal Rule Evaluation Summary" in full_text_norm
    assert "9. Detailed Rule Findings" in full_text_norm
    assert "10. Backward Evidence Traceability Graph" in full_text_norm
    assert "11. Uncertainty, Conflicts & Review Items" in full_text_norm
    assert "12. Chain of Custody & Audit Information" in full_text_norm
    assert "13. Cryptographic Integrity Manifest" in full_text_norm
    assert "14. Dossier Generation Metadata" in full_text_norm

    # Required Data Content
    assert inspection.inspection_number in full_text_norm
    assert "Metrixa Foods" in full_text_norm
    assert "Atta Whole Wheat" in full_text_norm
    assert "PCR-2011-R06-1-C" in full_text_norm
    assert "PCR-2011-R06-1-DA" in full_text_norm
    assert "PCR-2011-R09-1-PDP" in full_text_norm
    assert surface.sha256_hash[:16] in full_text_norm
    assert snapshot.integrity_hash[:16] in full_text_norm

@pytest.mark.asyncio
async def test_pdf_dossier_with_missing_optional_evidence():
    """Verify generator handles missing surfaces, uncalibrated geometry, and empty OCR gracefully."""
    insp_id = uuid.uuid4()
    inspection = Inspection(
        id=insp_id,
        inspection_number="INSP-EMPTY-TEST",
        initiated_at=datetime.now(timezone.utc),
    )
    snapshot = EvidenceSnapshot(
        id=uuid.uuid4(),
        inspection_id=insp_id,
        integrity_hash="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    )

    generator = DossierPDFGenerator(storage_service=None)
    result = await generator.generate_dossier(
        inspection=inspection,
        surfaces=[],
        ocr_runs=[],
        observations=[],
        geometries=[],
        evaluations=[],
        audit_logs=[],
        snapshot=snapshot,
        report_version=1,
    )

    assert result.pdf_bytes is not None
    assert len(result.pdf_bytes) > 0

    reader = PdfReader(io.BytesIO(result.pdf_bytes))
    full_text = "".join(p.extract_text() or "" for p in reader.pages)
    full_text_norm = " ".join(full_text.split())

    assert "METRIXA" in full_text_norm
    assert "Physical measurement unavailable - no valid calibration evidence" in full_text_norm
    assert "No ambiguous, conflicting, or indeterminate findings recorded" in full_text_norm
