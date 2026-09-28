import uuid
import hashlib
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_evidence_graph_traceability(
    client: AsyncClient,
    inspector_token: str,
    adjudicator_token: str
):
    """
    Test end-to-end evidence graph traceability:
    Verifies that a legal finding can be traced backward:
    RuleDefinition
      → RuleEvaluation
      → Observation
      → OCRRegion
      → InspectionSurface (with original image SHA-256)
      → Inspection
      → Product
      → Timestamps
    """
    insp_headers = {"Authorization": f"Bearer {inspector_token}"}
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}

    # 1. Create Product
    gtin = f"890{uuid.uuid4().hex[:10]}"
    prod_resp = await client.post("/api/v1/products", json={
        "gtin_barcode": gtin,
        "brand_name": "Tata Tea",
        "product_name": "Premium Leaf Tea 500g",
        "category": "Beverages",
        "commodity_type": "Tea",
    }, headers=insp_headers)
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["data"]["id"]

    # 2. Create Rule Definition (Rule 6(1)(c) - Net Quantity Standard Metric Units)
    rule_code = f"LMR_TEST_R6_1_C_{uuid.uuid4().hex[:6]}"
    rule_resp = await client.post("/api/v1/rules/definitions", json={
        "rule_code": rule_code,
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(c)",
        "clause_reference": "Rule 6 Subrule (1) Clause (c) read with Rule 12",
        "title": "Net Quantity in Standard Units of Weight or Measure",
        "description": "The net quantity in terms of the standard unit of weight or measure of the commodity contained in the package.",
        "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "source_url": "https://consumeraffairs.gov.in",
        "parameters": {"allowed_units": ["g", "kg", "ml", "l", "m", "cm", "N", "U"]},
        "evaluation_logic": {"standard_unit_check": True},
        "severity": "MANDATORY",
        "is_active": True
    }, headers=adj_headers)
    assert rule_resp.status_code == 201
    rule_id = rule_resp.json()["data"]["id"]

    # 3. Create Inspection linking to Product
    ins_resp = await client.post("/api/v1/inspections", json={
        "product_id": prod_id,
        "retail_outlet_name": "Reliance Smart Superstore Bandra",
        "notes": "Testing evidence chain traceability"
    }, headers=insp_headers)
    assert ins_resp.status_code == 201
    ins_id = ins_resp.json()["data"]["id"]

    # 4. Register Surface with SHA-256 Hash
    img_bytes = b"sample_tea_package_front_pdp_binary"
    img_hash = hashlib.sha256(img_bytes).hexdigest()
    surf_resp = await client.post("/api/v1/surfaces", json={
        "inspection_id": ins_id,
        "surface_type": "FRONT_PDP",
        "image_storage_path": "storage/packages/tea_pdp_master.jpg",
        "sha256_hash": img_hash,
        "image_width": 2400,
        "image_height": 1600,
        "file_size_bytes": len(img_bytes),
        "quality_metrics": {"blur_variance": 420.0, "glare_ratio": 0.02}
    }, headers=insp_headers)
    assert surf_resp.status_code == 201
    surface_id = surf_resp.json()["data"]["id"]

    # 5. Register OCR Region
    bbox = {"ymin": 0.82, "xmin": 0.20, "ymax": 0.86, "xmax": 0.38}
    ocr_resp = await client.post(f"/api/v1/surfaces/{surface_id}/ocr-regions", json=[{
        "raw_text": "Net Quantity: 500 g",
        "confidence": 0.99,
        "bounding_box": bbox,
        "token_order": 1
    }], headers=insp_headers)
    assert ocr_resp.status_code == 201
    ocr_region_id = ocr_resp.json()["data"][0]["id"]

    # 6. Record Observation linking to OCR Region and Surface
    obs_resp = await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surface_id,
        "ocr_region_id": ocr_region_id,
        "field_type": "NET_QUANTITY_VALUE",
        "raw_value": "Net Quantity: 500 g",
        "normalized_value": {"quantity": 500, "unit": "g", "is_standard_unit": True},
        "source": "CAMERA_STREAM",
        "confidence": 0.99,
        "status": "OBSERVED",
        "bounding_box": bbox,
    }, headers=insp_headers)
    assert obs_resp.status_code == 201
    obs_id = obs_resp.json()["data"]["id"]

    # 7. Record Rule Evaluation linking to Rule Definition and Observation evidence
    eval_resp = await client.post("/api/v1/rules/evaluations", json={
        "inspection_id": ins_id,
        "rule_definition_id": rule_id,
        "outcome": "PASS",
        "legal_rationale": "Net quantity is declared as 500 g in standard metric unit 'g' conforming to Rule 6(1)(c) and Rule 12.",
        "statutory_citation": "Rule 6(1)(c) read with Rule 12 and Second Schedule",
        "evidence_references": {
            "observation_id": obs_id,
            "surface_id": surface_id,
            "ocr_region_id": ocr_region_id,
            "bounding_box": bbox,
            "master_image_sha256": img_hash
        }
    }, headers=insp_headers)
    assert eval_resp.status_code == 201
    eval_id = eval_resp.json()["data"]["id"]

    # 8. TRAVERSE AND VERIFY THE COMPLETE EVIDENCE GRAPH:
    # Fetch Inspection Detail
    detail_resp = await client.get(f"/api/v1/inspections/{ins_id}", headers=insp_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]

    # Trace backward from RuleEvaluation to Product
    eval_found = next(e for e in detail["evaluations"] if e["id"] == eval_id)
    assert eval_found["rule_definition_id"] == rule_id
    assert eval_found["evidence_references"]["observation_id"] == obs_id
    assert eval_found["evidence_references"]["master_image_sha256"] == img_hash

    obs_found = next(o for o in detail["observations"] if o["id"] == obs_id)
    assert obs_found["surface_id"] == surface_id
    assert obs_found["ocr_region_id"] == ocr_region_id
    assert obs_found["raw_value"] == "Net Quantity: 500 g"

    surf_found = next(s for s in detail["surfaces"] if s["id"] == surface_id)
    assert surf_found["sha256_hash"] == img_hash

    assert detail["product"]["id"] == prod_id
    assert detail["product"]["gtin_barcode"] == gtin
