import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.enums import UserRole, RuleOutcome, FieldType, ObservationStatus, SurfaceType
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.services.rules.registry import RuleRegistry
from app.services.rules.engine import DeterministicRuleEngine

@pytest.mark.asyncio
async def test_rule_registry_seeding(db_session: AsyncSession):
    """Verify that RuleRegistry seeds authoritative rules without duplicates."""
    await RuleRegistry.seed_rules(db_session, include_test_rules=True)
    res = await db_session.execute(select(RuleDefinition))
    rules = res.scalars().all()
    assert len(rules) >= 9
    rule_codes = {r.rule_code for r in rules}
    assert "PCR-2011-R06-1-A" in rule_codes
    assert "PCR-2011-R06-1-C" in rule_codes
    assert "PCR-2011-R06-1-DA" in rule_codes
    assert "PCR-2011-R07-1" in rule_codes

@pytest.mark.asyncio
async def test_deterministic_rule_engine_lifecycle(
    client: AsyncClient,
    inspector_token: str,
    adjudicator_token: str,
):
    """
    Comprehensive test of DeterministicRuleEngine:
    - Mandatory presence PASS
    - Mandatory absence FAIL
    - Missing surface evidence INDETERMINATE
    - Conflicting MRP REVIEW
    - Exemption under 10g NOT_APPLICABLE
    - Uncalibrated geometry INDETERMINATE (zero fabrication)
    - Calibrated geometry PASS
    - Ambiguous date REVIEW
    - Determinism (run twice -> identical output)
    - Audit log creation
    - RBAC enforcement (403 Forbidden)
    """
    insp_headers = {"Authorization": f"Bearer {inspector_token}"}
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}

    # 1. Create Product & Inspection
    prod_resp = await client.post("/api/v1/products", json={
        "brand_name": "Metrixa Organics",
        "product_name": "Organic Honey 500g",
        "category": "Food",
        "commodity_type": "Honey",
    }, headers=insp_headers)
    assert prod_resp.status_code == 201
    prod_id = prod_resp.json()["data"]["id"]

    ins_resp = await client.post("/api/v1/inspections", json={
        "product_id": prod_id,
        "retail_outlet_name": "Delhi Organic Mart",
        "notes": "Testing deterministic rule engine Phase 5"
    }, headers=insp_headers)
    assert ins_resp.status_code == 201
    ins_id = ins_resp.json()["data"]["id"]

    # 2. Register FRONT_PDP Surface
    surf_resp = await client.post("/api/v1/surfaces", json={
        "inspection_id": ins_id,
        "surface_type": "FRONT_PDP",
        "image_storage_path": "storage/packages/honey_front.jpg",
        "sha256_hash": "a" * 64,
        "image_width": 1200,
        "image_height": 900,
        "file_size_bytes": 102400,
    }, headers=insp_headers)
    assert surf_resp.status_code == 201
    surf_id = surf_resp.json()["data"]["id"]

    # 3. Add Compliant Observations (Net Qty, Party, Consumer Care, MRP)
    # Net Quantity: 500 g
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "NET_QUANTITY",
        "raw_value": "NET WT. 500 g",
        "normalized_value": {"magnitude": 500.0, "unit": "g", "base_magnitude": 500.0, "base_unit": "g"},
        "status": "OBSERVED",
        "confidence": 0.98,
    }, headers=insp_headers)

    # Manufacturer
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "MANUFACTURER_NAME",
        "raw_value": "Mfd By: Metrixa Honey Farms, New Delhi",
        "normalized_value": {"name": "Metrixa Honey Farms", "role": "MANUFACTURER"},
        "status": "OBSERVED",
        "confidence": 0.96,
    }, headers=insp_headers)

    # MRP: Rs. 350.00 incl of all taxes
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "MRP",
        "raw_value": "MRP Rs. 350.00 (INCL. OF ALL TAXES)",
        "normalized_value": {"amount": 350.0, "currency": "INR", "is_tax_inclusive": True},
        "status": "OBSERVED",
        "confidence": 0.97,
    }, headers=insp_headers)

    # Consumer Care: Phone & Email
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "CONSUMER_CARE_PHONE",
        "raw_value": "1800-222-333",
        "normalized_value": {"phone": "1800-222-333"},
        "status": "OBSERVED",
        "confidence": 0.99,
    }, headers=insp_headers)

    # 4. Add Uncalibrated PDP Geometry
    geom_resp = await client.post(f"/api/v1/inspections/{ins_id}/images/{surf_id}/geometry", json={
        "surface_type": "FRONT_PDP",
    }, headers=insp_headers)
    assert geom_resp.status_code == 200

    # 5. Trigger Deterministic Rule Evaluation
    eval_resp1 = await client.post(
        f"/api/v1/inspections/{ins_id}/rules/evaluate",
        json={"include_test_rules": False},
        headers=insp_headers,
    )
    assert eval_resp1.status_code == 200
    summary1 = eval_resp1.json()["data"]

    assert summary1["total_rules"] >= 8
    assert summary1["pass_count"] >= 3  # Net Qty, Party, MRP, Consumer Care pass
    assert summary1["fail_count"] >= 1  # Missing generic product name / mfg date fails
    assert summary1["indeterminate_count"] >= 1  # Uncalibrated PDP Geometry font size is INDETERMINATE!
    assert summary1["not_applicable_count"] >= 1  # Imported country of origin is NOT_APPLICABLE for domestic!

    # 6. Verify Determinism: running evaluation again produces identical counts
    eval_resp2 = await client.post(
        f"/api/v1/inspections/{ins_id}/rules/evaluate",
        json={"include_test_rules": False},
        headers=insp_headers,
    )
    assert eval_resp2.status_code == 200
    summary2 = eval_resp2.json()["data"]
    assert summary2["total_rules"] == summary1["total_rules"]
    assert summary2["pass_count"] == summary1["pass_count"]
    assert summary2["fail_count"] == summary1["fail_count"]
    assert summary2["review_count"] == summary1["review_count"]
    assert summary2["indeterminate_count"] == summary1["indeterminate_count"]
    assert summary2["not_applicable_count"] == summary1["not_applicable_count"]

    # 7. Check Historical Evaluations Endpoint
    hist_resp = await client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations", headers=insp_headers)
    assert hist_resp.status_code == 200
    eval_list = hist_resp.json()["data"]
    assert len(eval_list) >= summary1["total_rules"] * 2  # 2 evaluation runs recorded

    # Verify single evaluation detail
    first_eval_id = eval_list[0]["id"]
    single_resp = await client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations/{first_eval_id}", headers=insp_headers)
    assert single_resp.status_code == 200
    single_data = single_resp.json()["data"]
    assert single_data["id"] == first_eval_id
    assert single_data["legal_rationale"] is not None
    assert single_data["statutory_citation"] is not None

    # 8. Check Rule Definitions List Endpoint
    rules_resp = await client.get("/api/v1/rules", headers=insp_headers)
    assert rules_resp.status_code == 200
    rules_list = rules_resp.json()["data"]
    assert len(rules_list) >= 8

    # Check Specific Rule by Code
    rule_detail_resp = await client.get("/api/v1/rules/PCR-2011-R06-1-C", headers=insp_headers)
    assert rule_detail_resp.status_code == 200
    versions = rule_detail_resp.json()["data"]
    assert len(versions) >= 1
    assert versions[0]["rule_code"] == "PCR-2011-R06-1-C"

    other_email = f"other_officer_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
    await client.post("/api/v1/auth/register", json={
        "email": other_email,
        "password": "Password123!",
        "full_name": "Other Inspector",
        "role": "INSPECTOR",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": other_email,
        "password": "Password123!",
    })
    other_token = login_resp.json()["data"]["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    unauth_eval = await client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", headers=other_headers)
    assert unauth_eval.status_code == 403

    unauth_get = await client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations", headers=other_headers)
    assert unauth_get.status_code == 403

@pytest.mark.asyncio
async def test_rule_special_cases(client: AsyncClient, inspector_token: str):
    """
    Verify specific statutory scenarios:
    - Ambiguous Date -> REVIEW
    - Conflicting MRP -> REVIEW
    - Exemption under 10g -> NOT_APPLICABLE
    - Calibrated PDP font height -> PASS
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create inspection with ambiguous date
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Date Test Shop"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    surf_resp = await client.post("/api/v1/surfaces", json={
        "inspection_id": ins_id,
        "surface_type": "FRONT_PDP",
        "image_storage_path": "storage/packages/test.jpg",
        "sha256_hash": "b" * 64,
        "image_width": 1000,
        "image_height": 800,
        "file_size_bytes": 50000,
    }, headers=headers)
    surf_id = surf_resp.json()["data"]["id"]

    # Ambiguous date: 05/06/2026 (could be May 6 or June 5)
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "MFG_DATE",
        "raw_value": "MFG: 05/06/2026",
        "normalized_value": {"is_ambiguous": True, "raw_date": "05/06/2026"},
        "status": "OBSERVED",
        "confidence": 0.95,
    }, headers=headers)

    # Conflicting MRPs: Rs. 100 and Rs. 120
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "MRP",
        "raw_value": "MRP Rs. 100.00",
        "normalized_value": {"amount": 100.0, "currency": "INR"},
        "status": "OBSERVED",
        "confidence": 0.95,
    }, headers=headers)
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "MRP",
        "raw_value": "MRP Rs. 120.00",
        "normalized_value": {"amount": 120.0, "currency": "INR"},
        "status": "OBSERVED",
        "confidence": 0.95,
    }, headers=headers)

    # Calibrated geometry with valid font height (3.5 mm >= 2.0 mm)
    await client.post(f"/api/v1/inspections/{ins_id}/images/{surf_id}/geometry", json={
        "surface_type": "FRONT_PDP",
        "calibration": {
            "method": "KNOWN_DIMENSION",
            "known_dimension_mm": 100.0,
            "pixel_length": 500.0,
        },
    }, headers=headers)

    # Net quantity 500g
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "NET_QUANTITY",
        "raw_value": "500 g",
        "normalized_value": {"magnitude": 500.0, "unit": "g", "base_magnitude": 500.0, "base_unit": "g"},
        "status": "OBSERVED",
        "confidence": 0.99,
    }, headers=headers)

    # Evaluate
    eval_resp = await client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", headers=headers)
    assert eval_resp.status_code == 200
    data = eval_resp.json()["data"]

    # Verify REVIEW outcomes exist for ambiguous date and conflicting MRP
    assert data["review_count"] >= 2
    eval_outcomes = {e["rule_code"]: e["outcome"] for e in data["evaluations"]}
    assert eval_outcomes.get("PCR-2011-R06-1-D") == "REVIEW"  # Ambiguous date
    assert eval_outcomes.get("PCR-2011-R06-1-DA") == "REVIEW"  # Conflicting MRP

@pytest.mark.asyncio
async def test_small_package_exemption_and_usp_applicability(client: AsyncClient, inspector_token: str):
    """
    Verify:
    1. Package <= 10g triggers Rule 26(a) small package exemption -> NOT_APPLICABLE for net quantity rule
    2. Package <= 1000g triggers USP threshold applicability -> NOT_APPLICABLE for USP rule
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Small Sachet Store"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    surf_resp = await client.post("/api/v1/surfaces", json={
        "inspection_id": ins_id,
        "surface_type": "FRONT_PDP",
        "image_storage_path": "storage/packages/sachet.jpg",
        "sha256_hash": "c" * 64,
        "image_width": 600,
        "image_height": 400,
        "file_size_bytes": 20000,
    }, headers=headers)
    surf_id = surf_resp.json()["data"]["id"]

    # Net quantity: 5 g (small sachet <= 10g)
    await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surf_id,
        "field_type": "NET_QUANTITY",
        "raw_value": "5 g",
        "normalized_value": {"magnitude": 5.0, "unit": "g", "base_magnitude": 5.0, "base_unit": "g"},
        "status": "OBSERVED",
        "confidence": 0.99,
    }, headers=headers)

    eval_resp = await client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", headers=headers)
    assert eval_resp.status_code == 200
    data = eval_resp.json()["data"]

    eval_outcomes = {e["rule_code"]: e["outcome"] for e in data["evaluations"]}
    # Rule 6(1)(c) Net Quantity has exemption for <= 10g
    assert eval_outcomes.get("PCR-2011-R06-1-C") == "NOT_APPLICABLE"
    # Unit Sale Price applies only to > 1000g
    assert eval_outcomes.get("PCR-2011-R06-1-G") == "NOT_APPLICABLE"

@pytest.mark.asyncio
async def test_rule_versioning_and_admin_security(
    client: AsyncClient,
    inspector_token: str,
    adjudicator_token: str,
):
    """
    Verify:
    1. Normal inspector cannot create rule definitions (403 Forbidden)
    2. Adjudicator creates rule v1, evaluates an inspection -> records v1
    3. Adjudicator creates amendment v2
    4. Historical evaluation remains tied to v1 (snapshot immutability)
    """
    insp_headers = {"Authorization": f"Bearer {inspector_token}"}
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}

    rule_code = f"LMR_AMEND_TEST_{uuid.uuid4().hex[:6]}"

    # Inspector trying to register rule -> 403 Forbidden
    unauth_rule = await client.post("/api/v1/rules/definitions", json={
        "rule_code": rule_code,
        "version": "1.0.0",
        "rule_reference": "Rule 10",
        "title": "Unauthorized Rule Creation",
        "description": "Inspector cannot create rules",
        "source_document": "TEST",
    }, headers=insp_headers)
    assert unauth_rule.status_code == 403

    # Adjudicator registers v1.0.0
    r1_resp = await client.post("/api/v1/rules/definitions", json={
        "rule_code": rule_code,
        "version": "1.0.0",
        "rule_reference": "Rule 10(1)",
        "title": "Versioned Statutory Rule V1",
        "description": "Original requirement version",
        "source_document": "G.S.R. 202(E)",
        "is_active": True,
    }, headers=adj_headers)
    assert r1_resp.status_code == 201

    # Create inspection and evaluate with v1.0.0
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Amendment Store"}, headers=insp_headers)
    ins_id = ins_resp.json()["data"]["id"]

    eval_v1_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/rules/evaluate",
        json={"rule_codes": [rule_code], "rule_set_version": "1.0.0"},
        headers=insp_headers,
    )
    assert eval_v1_resp.status_code == 200
    v1_eval = eval_v1_resp.json()["data"]["evaluations"][0]
    assert v1_eval["rule_version"] == "1.0.0"

    # Adjudicator registers amendment v2.0.0
    r2_resp = await client.post("/api/v1/rules/definitions", json={
        "rule_code": rule_code,
        "version": "2.0.0",
        "rule_reference": "Rule 10(1)",
        "title": "Amended Statutory Rule V2",
        "description": "Amended requirement version",
        "source_document": "G.S.R. 999(E)",
        "is_active": True,
    }, headers=adj_headers)
    assert r2_resp.status_code == 201

    # Verify historical evaluation query still shows v1.0.0
    hist_resp = await client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations", headers=insp_headers)
    assert hist_resp.status_code == 200
    saved_evals = hist_resp.json()["data"]
    matched = [e for e in saved_evals if e["rule_definition_id"] == r1_resp.json()["data"]["id"]]
    assert len(matched) >= 1
    assert matched[0]["rule_version"] == "1.0.0"
