import io
import uuid
import pytest
from PIL import Image, ImageDraw
from httpx import AsyncClient
from sqlalchemy import select, func

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.enums import UserRole, ObservationStatus, CorrectionType, RuleOutcome
from app.models.ocr_region import OCRRegion
from app.models.adjudication import OCRAdjudication
from app.models.observation import Observation
from app.models.audit_log import AuditLog
from app.models.rule_evaluation import RuleEvaluation

def create_test_image() -> bytes:
    img = Image.new("RGB", (400, 300), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "NET QUANTITY: 500 g", fill=(0, 0, 0))
    draw.text((20, 60), "MRP Rs. 150.00", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.fixture
async def setup_inspection_with_ocr_and_entities(client: AsyncClient, inspector_token: str):
    headers = {"Authorization": f"Bearer {inspector_token}"}
    # 1. Create inspection
    ins_res = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Adjudication Test Mart"}, headers=headers)
    assert ins_res.status_code == 201
    ins_id = ins_res.json()["data"]["id"]

    # 2. Upload image
    img_bytes = create_test_image()
    files = {"file": ("front.png", img_bytes, "image/png")}
    up_res = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers)
    assert up_res.status_code == 201
    image_id = up_res.json()["data"]["id"]

    # 3. Run OCR
    ocr_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"provider_name": "mock"},
        headers=headers,
    )
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()["data"]
    ocr_run_id = ocr_data["id"]

    # 4. Run entity parsing
    ent_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/entities",
        json={"ocr_run_id": ocr_run_id},
        headers=headers,
    )
    assert ent_res.status_code == 200

    # 5. Evaluate rules
    rule_res = await client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", headers=headers)
    assert rule_res.status_code == 200

    return {
        "inspection_id": ins_id,
        "image_id": image_id,
        "ocr_run_id": ocr_run_id,
        "regions": ocr_data.get("regions", []),
    }

@pytest.mark.asyncio
async def test_get_adjudication_workspace(client: AsyncClient, inspector_token: str, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    res = await client.get(f"/api/v1/inspections/{ins_id}/adjudication", headers=headers)
    assert res.status_code == 200
    ws = res.json()["data"]

    assert ws["inspection_id"] == ins_id
    assert len(ws["surfaces"]) >= 1
    assert len(ws["regions"]) >= 1
    assert len(ws["observations"]) >= 1
    assert "conflicts" in ws
    assert ws["evaluation_run_id"] is not None

@pytest.mark.asyncio
async def test_ocr_region_correction_preserves_immutability(client: AsyncClient, inspector_token: str, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    regions = data["regions"]
    assert len(regions) > 0
    target_reg = regions[0]
    reg_id = target_reg["id"]
    orig_text = target_reg["raw_text"]

    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Patch OCR region (Text & Bounding Box)
    patch_payload = {
        "raw_text": "CORRECTED REGION TEXT 500 g",
        "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.08},
        "reason": "Inspector corrected blurry OCR reading",
    }
    res = await client.patch(f"/api/v1/inspections/{ins_id}/ocr-regions/{reg_id}", json=patch_payload, headers=headers)
    assert res.status_code == 200
    patched = res.json()["data"]

    assert patched["status"] == "CORRECTED"
    assert patched["raw_text"] == "CORRECTED REGION TEXT 500 g"
    assert patched["original_text"] == orig_text
    assert patched["is_adjudicated"] is True
    assert patched["revision"] == 1

    # ARCHITECTURAL SAFEGUARD: Verify original OCRRegion row in database is 100% UNCHANGED
    db_reg_res = await db_session.execute(select(OCRRegion).where(OCRRegion.id == uuid.UUID(reg_id)))
    db_reg = db_reg_res.scalar_one()
    assert db_reg.raw_text == orig_text  # Unmutated!

    # Verify dedicated OCRAdjudication row was created
    adj_res = await db_session.execute(select(OCRAdjudication).where(OCRAdjudication.ocr_region_id == uuid.UUID(reg_id)))
    adj_record = adj_res.scalar_one()
    assert adj_record.corrected_text == "CORRECTED REGION TEXT 500 g"
    assert adj_record.original_text == orig_text
    assert adj_record.revision == 1
    assert adj_record.is_active is True

    # Verify AuditLog recorded action
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.inspection_id == uuid.UUID(ins_id), AuditLog.action == "OCR_REGION_EDITED")
    )
    audit = audit_res.scalar_one_or_none()
    assert audit is not None
    assert audit.justification == "Inspector corrected blurry OCR reading"

@pytest.mark.asyncio
async def test_ocr_region_rejection(client: AsyncClient, inspector_token: str, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    regions = data["regions"]
    target_reg = regions[0]
    reg_id = target_reg["id"]
    orig_text = target_reg["raw_text"]

    headers = {"Authorization": f"Bearer {inspector_token}"}

    reject_res = await client.post(
        f"/api/v1/inspections/{ins_id}/ocr-regions/{reg_id}/reject",
        json={"reason": "Spurious reflection artifact detected as text"},
        headers=headers,
    )
    assert reject_res.status_code == 200
    rej = reject_res.json()["data"]
    assert rej["status"] == "REJECTED"
    assert rej["confidence"] == 0.0

    # Verify original OCRRegion row remains unchanged
    db_reg_res = await db_session.execute(select(OCRRegion).where(OCRRegion.id == uuid.UUID(reg_id)))
    db_reg = db_reg_res.scalar_one()
    assert db_reg.raw_text == orig_text

@pytest.mark.asyncio
async def test_bounding_box_validation(client: AsyncClient, inspector_token: str, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    reg_id = data["regions"][0]["id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Test out of bounds: x + width > 1.0
    invalid_payload = {
        "bounding_box": {"x": 0.8, "y": 0.1, "width": 0.4, "height": 0.2},  # 0.8 + 0.4 = 1.2 > 1.0
        "reason": "Testing validation",
    }
    res = await client.patch(f"/api/v1/inspections/{ins_id}/ocr-regions/{reg_id}", json=invalid_payload, headers=headers)
    assert res.status_code == 422  # Unprocessable Entity

    # Test negative coordinate
    neg_payload = {
        "bounding_box": {"x": -0.1, "y": 0.1, "width": 0.3, "height": 0.2},
        "reason": "Testing validation",
    }
    res2 = await client.patch(f"/api/v1/inspections/{ins_id}/ocr-regions/{reg_id}", json=neg_payload, headers=headers)
    assert res2.status_code == 422

@pytest.mark.asyncio
async def test_create_manual_ocr_region(client: AsyncClient, inspector_token: str, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    surf_id = data["image_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    payload = {
        "surface_id": surf_id,
        "raw_text": "MANUAL OCR TAG: RS 99.00",
        "bounding_box": {"x": 0.05, "y": 0.8, "width": 0.25, "height": 0.05},
        "reason": "Officer identified faint stamp missed by automated OCR",
    }
    res = await client.post(f"/api/v1/inspections/{ins_id}/ocr-regions", json=payload, headers=headers)
    assert res.status_code == 201
    created = res.json()["data"]
    assert created["status"] == "MANUAL"
    assert created["raw_text"] == "MANUAL OCR TAG: RS 99.00"
    assert created["correction_type"] == "REGION_CREATED"

@pytest.mark.asyncio
async def test_observation_verification_and_correction_chain(client: AsyncClient, inspector_token: str, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Fetch observations
    obs_res = await client.get(f"/api/v1/inspections/{ins_id}/observations", headers=headers)
    assert obs_res.status_code == 200
    observations = obs_res.json()["data"]
    assert len(observations) > 0
    target_obs = observations[0]
    obs_id = target_obs["id"]

    # 1. Verify observation
    v_res = await client.post(
        f"/api/v1/inspections/{ins_id}/observations/{obs_id}/verify",
        json={"reason": "Officer verified against physical package"},
        headers=headers,
    )
    assert v_res.status_code == 200
    v_obs = v_res.json()["data"]
    assert v_obs["status"] == "VERIFIED"
    assert v_obs["confidence"] == 1.0
    assert v_obs["revision"] == 2

    # Verify prior revision was superseded and preserved
    prior_db_res = await db_session.execute(select(Observation).where(Observation.id == uuid.UUID(obs_id)))
    prior_db = prior_db_res.scalar_one()
    assert prior_db.is_latest is False
    assert prior_db.superseded_by_id == uuid.UUID(v_obs["id"])

    # 2. Correct verified observation
    c_res = await client.post(
        f"/api/v1/inspections/{ins_id}/observations/{v_obs['id']}/correct",
        json={
            "raw_value": "Corrected Net Wt 500 g",
            "normalized_value": {"value": 500.0, "unit": "g", "display": "500 g"},
            "reason": "Officer corrected OCR typo in unit",
        },
        headers=headers,
    )
    assert c_res.status_code == 200
    c_obs = c_res.json()["data"]
    assert c_obs["revision"] == 3
    assert c_obs["raw_value"] == "Corrected Net Wt 500 g"
    assert c_obs["is_latest"] is True

@pytest.mark.asyncio
async def test_manual_observation_creation_and_provenance(client: AsyncClient, inspector_token: str, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    payload = {
        "field_type": "COUNTRY_OF_ORIGIN",
        "raw_value": "Made in India",
        "normalized_value": {"country": "IND", "display": "India"},
        "reason": "Officer verified country of origin declaration on bottom surface stamp",
    }
    res = await client.post(f"/api/v1/inspections/{ins_id}/observations/manual", json=payload, headers=headers)
    assert res.status_code == 201
    man_obs = res.json()["data"]

    assert man_obs["source"] == "OFFICER_INPUT"
    assert man_obs["status"] == "VERIFIED"
    assert man_obs["confidence"] == 1.0
    assert man_obs["revision"] == 1

    # Check AuditLog
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.inspection_id == uuid.UUID(ins_id), AuditLog.action == "MANUAL_OBSERVATION_CREATED")
    )
    audit = audit_res.scalar_one_or_none()
    assert audit is not None
    assert audit.justification == payload["reason"]

@pytest.mark.asyncio
async def test_conflict_detection_in_workspace(client: AsyncClient, inspector_token: str, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Add a second conflicting manual observation for NET_QUANTITY
    await client.post(
        f"/api/v1/inspections/{ins_id}/observations/manual",
        json={
            "field_type": "NET_QUANTITY",
            "raw_value": "750 g",
            "reason": "Conflicting declaration found on inner pouch",
        },
        headers=headers,
    )

    ws_res = await client.get(f"/api/v1/inspections/{ins_id}/adjudication", headers=headers)
    assert ws_res.status_code == 200
    ws = ws_res.json()["data"]

    net_qty_conflicts = [c for c in ws["conflicts"] if c["field_type"] == "NET_QUANTITY"]
    assert len(net_qty_conflicts) == 1
    assert net_qty_conflicts[0]["has_conflict"] is True
    assert len(net_qty_conflicts[0]["observations"]) >= 2

@pytest.mark.asyncio
async def test_deterministic_rule_reevaluation(client: AsyncClient, inspector_token: str, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Fetch initial evaluations count
    init_evals = await db_session.execute(select(func.count(RuleEvaluation.id)).where(RuleEvaluation.inspection_id == uuid.UUID(ins_id)))
    initial_count = init_evals.scalar()

    # Re-evaluate rules
    reeval_res = await client.post(f"/api/v1/inspections/{ins_id}/rules/re-evaluate", headers=headers)
    assert reeval_res.status_code == 200
    reeval_data = reeval_res.json()["data"]

    assert reeval_data["new_evaluation_run_id"] is not None
    assert reeval_data["previous_evaluation_run_id"] is not None
    assert reeval_data["new_evaluation_run_id"] != reeval_data["previous_evaluation_run_id"]
    assert len(reeval_data["changes"]) > 0

    # ARCHITECTURAL SAFEGUARD: Historical rule evaluations are PRESERVED (count increased, not replaced)
    after_evals = await db_session.execute(select(func.count(RuleEvaluation.id)).where(RuleEvaluation.inspection_id == uuid.UUID(ins_id)))
    after_count = after_evals.scalar()
    assert after_count > initial_count

@pytest.mark.asyncio
async def test_unauthorized_adjudication_receives_403(client: AsyncClient, db_session, setup_inspection_with_ocr_and_entities):
    data = setup_inspection_with_ocr_and_entities
    ins_id = data["inspection_id"]

    # Create another inspector who is NOT assigned to this inspection
    other_inspector = User(
        email=f"other_{uuid.uuid4().hex[:6]}@metrixa.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Other Officer",
        role=UserRole.INSPECTOR,
        is_active=True,
    )
    db_session.add(other_inspector)
    await db_session.commit()
    await db_session.refresh(other_inspector)

    other_token = create_access_token({"sub": str(other_inspector.id), "email": other_inspector.email, "role": other_inspector.role.value})
    unauth_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempt to access adjudication workspace -> 403 Forbidden
    ws_res = await client.get(f"/api/v1/inspections/{ins_id}/adjudication", headers=unauth_headers)
    assert ws_res.status_code == 403

    # Attempt to create manual observation -> 403 Forbidden
    post_res = await client.post(
        f"/api/v1/inspections/{ins_id}/observations/manual",
        json={"field_type": "MRP", "raw_value": "100", "reason": "Unauthorized attempt"},
        headers=unauth_headers,
    )
    assert post_res.status_code == 403
