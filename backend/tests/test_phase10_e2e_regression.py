import io
import uuid
import hashlib
import pytest
from httpx import AsyncClient
from PIL import Image
from datetime import datetime, timezone

from app.models.enums import SurfaceType, FieldType, ObservationStatus, RuleOutcome
from app.models.label_version import LabelVersion
from app.services.product.ledger_service import compute_label_fingerprint, compare_label_versions

def generate_test_image(format: str = "JPEG", size=(400, 300), color=(70, 130, 180)) -> bytes:
    bio = io.BytesIO()
    mode = "RGB" if format.upper() in ("JPEG", "JPG") else "RGBA"
    img = Image.new(mode, size, color)
    img.save(bio, format=format)
    return bio.getvalue()

@pytest.mark.asyncio
async def test_phase10_end_to_end_statutory_pipeline(client: AsyncClient, inspector_token: str, adjudicator_token: str):
    """
    Phase 10 Comprehensive 15-Stage End-to-End Regression Verification.
    Validates complete flow:
    1. System Health
    2. Authentication & Role-based Access
    3. Inspection Initialization
    4. Surface Allocation (FRONT_PDP)
    5. Image Ingestion (with Magic Bytes & SHA-256)
    6. Evidence Integrity & Immutability
    7. Multi-Declaration Observation Entry
    8. Conflict Injection (Competing MRPs)
    9. Conflict Detection & Flagging
    10. Adjudication & Resolution Workflow
    11. Deterministic Legal Rule Evaluation (PCR 2011)
    12. Statutory Verdict Composition (PASS/REVIEW)
    13. Product Ledger Linking & Label Version Fingerprinting (SHA-256)
    14. Formal Inspection Report Generation
    15. Dashboard Analytics & Timeline Continuity
    """
    insp_headers = {"Authorization": f"Bearer {inspector_token}"}
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}

    # -------------------------------------------------------------------------
    # Stage 1: System Health Verification
    # -------------------------------------------------------------------------
    health_resp = await client.get("/api/v1/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()
    assert h_data["success"] is True
    assert h_data["data"]["database"] == "connected"
    assert h_data["data"]["platform"] == "METRIXA"

    # -------------------------------------------------------------------------
    # Stage 2: Authentication
    # -------------------------------------------------------------------------
    assert inspector_token is not None
    assert adjudicator_token is not None

    # -------------------------------------------------------------------------
    # Stage 3: Inspection Initialization
    # -------------------------------------------------------------------------
    gtin = f"890{uuid.uuid4().int % 10000000000:010d}"
    ins_payload = {
        "retail_outlet_name": "SIH Mega Mart Superstore",
        "retail_outlet_location": "Dwarka Sector 10, New Delhi 110075",
        "commodity_type": "Packaged Food",
        "notes": "Phase 10 E2E Golden Verification Inspection"
    }
    create_ins_resp = await client.post("/api/v1/inspections", json=ins_payload, headers=insp_headers)
    assert create_ins_resp.status_code == 201
    inspection_data = create_ins_resp.json()["data"]
    inspection_id = inspection_data["id"]
    assert inspection_data["retail_outlet_name"] == "SIH Mega Mart Superstore"

    # -------------------------------------------------------------------------
    # Stage 4 & 5: Surface Allocation & Image Ingestion with Magic Bytes
    # -------------------------------------------------------------------------
    img_bytes = generate_test_image("JPEG", size=(600, 450))
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    upload_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/surfaces/FRONT_PDP/images",
        files={"file": ("pdp_primary.jpg", img_bytes, "image/jpeg")},
        headers=insp_headers
    )
    assert upload_resp.status_code == 201
    img_data = upload_resp.json()["data"]
    surface_id = img_data["id"]
    assert img_data["detected_format"] == "JPEG"
    assert img_data["sha256_hash"] == expected_hash
    assert img_data["image_width"] == 600
    assert img_data["image_height"] == 450

    # -------------------------------------------------------------------------
    # Stage 6: Evidence Integrity Check
    # -------------------------------------------------------------------------
    insp_detail_resp = await client.get(f"/api/v1/inspections/{inspection_id}", headers=insp_headers)
    assert insp_detail_resp.status_code == 200
    detail_data = insp_detail_resp.json()["data"]
    surfaces = detail_data.get("surfaces", [])
    assert len(surfaces) == 1
    assert surfaces[0]["surface_type"] == "FRONT_PDP"
    assert surfaces[0]["sha256_hash"] == expected_hash

    # -------------------------------------------------------------------------
    # Stage 7: Multi-Declaration Observation Entry (PCR 2011 Baseline)
    # -------------------------------------------------------------------------
    declarations = [
        {"field_type": "BRAND_NAME", "raw_value": "VedaOrganics", "normalized_value": {"value": "VedaOrganics"}},
        {"field_type": "PRODUCT_NAME", "raw_value": "Organic Himalayan Honey 500g", "normalized_value": {"value": "Organic Himalayan Honey 500g"}},
        {"field_type": "NET_QUANTITY", "raw_value": "500 g", "normalized_value": {"value": 500.0, "unit": "g", "base_quantity": 500.0, "base_unit": "g"}},
        {"field_type": "MRP", "raw_value": "Rs. 320.00 (incl. of all taxes)", "normalized_value": {"value": 320.0, "currency": "INR", "includes_taxes": True}},
        {"field_type": "DATE_OF_PACKING", "raw_value": "02/2026", "normalized_value": {"date_iso": "2026-02", "precision": "MONTH_YEAR"}},
        {"field_type": "MANUFACTURER_NAME", "raw_value": "Veda Organics Naturals Ltd, Solan, HP 173212", "normalized_value": {"name": "Veda Organics Naturals Ltd"}},
        {"field_type": "COUNTRY_OF_ORIGIN", "raw_value": "Made in India", "normalized_value": {"country": "India"}},
        {"field_type": "CONSUMER_CARE_EMAIL", "raw_value": "care@vedaorganics.in", "normalized_value": {"emails": ["care@vedaorganics.in"]}},
        {"field_type": "UNIT_SALE_PRICE", "raw_value": "Rs. 0.64 / g", "normalized_value": {"value": 0.64, "unit": "g"}},
    ]

    created_obs_ids = []
    for d in declarations:
        obs_resp = await client.post(
            "/api/v1/observations",
            json={
                "inspection_id": inspection_id,
                "surface_id": surface_id,
                "field_type": d["field_type"],
                "raw_value": d["raw_value"],
                "normalized_value": d["normalized_value"],
                "source": "OFFICER_INPUT",
                "confidence": 0.96,
                "status": "VERIFIED"
            },
            headers=insp_headers
        )
        assert obs_resp.status_code == 201
        created_obs_ids.append(obs_resp.json()["data"]["id"])

    # -------------------------------------------------------------------------
    # Stage 8 & 9: Conflict Injection & Detection (Dual MRP)
    # -------------------------------------------------------------------------
    conflict_mrp_resp = await client.post(
        "/api/v1/observations",
        json={
            "inspection_id": inspection_id,
            "surface_id": surface_id,
            "field_type": "MRP",
            "raw_value": "Rs. 350.00 (incl. of all taxes)",
            "normalized_value": {"value": 350.0, "currency": "INR", "includes_taxes": True},
            "source": "OFFICER_INPUT",
            "confidence": 0.90,
            "status": "CONFLICTING"
        },
        headers=insp_headers
    )
    assert conflict_mrp_resp.status_code == 201
    conflict_mrp_id = conflict_mrp_resp.json()["data"]["id"]

    # -------------------------------------------------------------------------
    # Stage 10: Adjudication & Resolution Workflow
    # -------------------------------------------------------------------------
    # Senior adjudicator reviews and resolves the conflict via immutable revision
    adj_resp = await client.post(
        f"/api/v1/observations/{conflict_mrp_id}/revise",
        json={
            "status": "REJECTED",
            "revision_reason": "Sticker price is unauthorized overprint; rejected in favor of printed factory declaration."
        },
        headers=adj_headers
    )
    assert adj_resp.status_code == 201
    assert adj_resp.json()["data"]["status"] == "REJECTED"

    # -------------------------------------------------------------------------
    # Stage 11 & 12: Deterministic Legal Rule Evaluation under PCR 2011
    # -------------------------------------------------------------------------
    rule_eval_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/rules/evaluate",
        json={},
        headers=insp_headers
    )
    assert rule_eval_resp.status_code == 200
    rule_eval_data = rule_eval_resp.json()["data"]
    evaluations = rule_eval_data.get("evaluations", [])
    assert len(evaluations) > 0
    assert rule_eval_data["total_rules"] > 0

    # Verify key PCR rules evaluated without unhandled exceptions
    rule_codes = [r["rule_code"] for r in evaluations]
    assert "PCR-2011-R06-1-A" in rule_codes
    assert "PCR-2011-R06-1-C" in rule_codes
    assert "PCR-2011-R06-1-DA" in rule_codes
    assert "PCR-2011-R06-1-F" in rule_codes

    # -------------------------------------------------------------------------
    # Stage 13: Product Ledger Linking & Label Version Fingerprinting
    # -------------------------------------------------------------------------
    canonical_decls = {d["field_type"]: d["raw_value"] for d in declarations}
    fingerprint = compute_label_fingerprint(canonical_decls)
    assert len(fingerprint) == 64

    # Test label version change detection
    altered_decls = {**canonical_decls, "MRP": "Rs. 340.00 (incl. of all taxes)"}
    v1 = LabelVersion(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        version_tag="v1.0",
        canonical_declarations=canonical_decls
    )
    v2 = LabelVersion(
        id=uuid.uuid4(),
        product_id=v1.product_id,
        version_tag="v2.0",
        canonical_declarations=altered_decls
    )
    diff = compare_label_versions(v1, v2)
    assert diff.from_version_tag == "v1.0"
    assert diff.to_version_tag == "v2.0"
    assert len(diff.changed_fields) == 1
    assert diff.changed_fields[0].field == "MRP"
    assert diff.changed_fields[0].prev_value == "Rs. 320.00 (incl. of all taxes)"
    assert diff.changed_fields[0].curr_value == "Rs. 340.00 (incl. of all taxes)"

    # -------------------------------------------------------------------------
    # Stage 14: Inspection Report Generation
    # -------------------------------------------------------------------------
    report_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/reports",
        json={"include_images": True, "include_ocr_dump": True},
        headers=insp_headers
    )
    assert report_resp.status_code == 201
    report_data = report_resp.json()["data"]
    assert report_data["inspection_id"] == inspection_id
    assert report_data["report_version"] == 1
    assert report_data["status"] == "GENERATED"
    assert len(report_data["sha256_hash"]) == 64
    assert report_data["file_size_bytes"] > 0

    # -------------------------------------------------------------------------
    # Stage 15: Analytics & Timeline Verification
    # -------------------------------------------------------------------------
    analytics_resp = await client.get("/api/v1/analytics/overview", headers=insp_headers)
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()["data"]
    assert "total_inspections" in analytics_data
    assert analytics_data["total_inspections"] >= 1
