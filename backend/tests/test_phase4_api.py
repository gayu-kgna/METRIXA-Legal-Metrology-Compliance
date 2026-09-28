import io
import uuid
import hashlib
import pytest
from PIL import Image, ImageDraw
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.enums import UserRole

def create_synthetic_commodity_image() -> bytes:
    """Create a synthetic package surface image with crisp Legal Metrology declarations."""
    salt = uuid.uuid4().bytes[:4]
    img = Image.new("RGB", (600, 450), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    draw.rectangle([10, 10, 590, 440], outline=(50, 50, 50), width=3)
    draw.text((30, 30), "METRIXA PREMIUM GREEN TEA", fill=(10, 10, 10))
    draw.text((30, 80), "Mfd By: Metrixa Foods Pvt Ltd, Plot 42, Industrial Area, New Delhi 110001", fill=(10, 10, 10))
    draw.text((30, 150), "NET QUANTITY: 500 g", fill=(10, 10, 10))
    draw.text((30, 200), "MRP Rs. 250.00 (INCL. OF ALL TAXES)", fill=(10, 10, 10))
    draw.text((30, 250), "MFG DATE: 01/2026", fill=(10, 10, 10))
    draw.text((30, 300), "CUSTOMER CARE: 1800-111-222", fill=(10, 10, 10))
    draw.text((30, 340), "EMAIL: care@metrixa.example.com", fill=(10, 10, 10))
    draw.text((30, 380), "Country of Origin: India", fill=(10, 10, 10))
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.mark.asyncio
async def test_end_to_end_entity_and_geometry_api(client: AsyncClient, inspector_token: str):
    """
    End-to-end integration test:
    1. Create inspection & upload image
    2. Run OCR (Mock provider)
    3. Run Entity Parsing API
    4. Validate structured observations & OCR source traceability
    5. Run PDP Geometry API (uncalibrated & calibrated)
    6. Retrieve historical entity and geometry runs
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create inspection & surface
    ins_res = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Phase 4 Test Supermarket"}, headers=headers)
    assert ins_res.status_code == 201
    ins_id = ins_res.json()["data"]["id"]

    img_bytes = create_synthetic_commodity_image()
    files = {"file": ("front_pdp.png", img_bytes, "image/png")}
    up_res = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers)
    assert up_res.status_code == 201
    image_id = up_res.json()["data"]["id"]

    # 2. Run OCR
    ocr_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"provider_name": "mock"},
        headers=headers,
    )
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()["data"]
    ocr_run_id = ocr_data["id"]

    # 3. Run Entity Parsing
    ent_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/entities",
        json={"ocr_run_id": ocr_run_id},
        headers=headers,
    )
    assert ent_res.status_code == 200
    ent_data = ent_res.json()["data"]
    assert ent_data["inspection_id"] == ins_id
    assert ent_data["surface_id"] == image_id
    assert ent_data["ocr_run_id"] == ocr_run_id
    assert ent_data["status"] == "COMPLETED"
    assert ent_data["total_entities_extracted"] > 0
    assert ent_data["parser_version"] == "ENTITY-PARSER-v1"
    assert ent_data["normalizer_version"] == "NORMALIZER-v1"

    # Verify generated observations
    observations = ent_data["observations"]
    assert len(observations) == ent_data["total_entities_extracted"]
    field_types = {o["field_type"] for o in observations}
    assert "NET_QUANTITY" in field_types
    assert "MRP" in field_types
    assert "DATE_OF_MANUFACTURE" in field_types
    assert "CONSUMER_CARE_PHONE" in field_types
    assert "CONSUMER_CARE_EMAIL" in field_types

    # Verify OCR source traceability in observation
    net_qty_obs = next(o for o in observations if o["field_type"] == "NET_QUANTITY")
    assert net_qty_obs["raw_value"] is not None
    assert net_qty_obs["normalized_value"]["value"] == 500.0
    assert net_qty_obs["normalized_value"]["unit"] == "g"
    assert "source_ocr_region_ids" in net_qty_obs["normalized_value"]
    assert len(net_qty_obs["normalized_value"]["source_ocr_region_ids"]) >= 1

    # 4. Retrieve historical entity runs
    hist_ent_res = await client.get(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/entities",
        headers=headers,
    )
    assert hist_ent_res.status_code == 200
    hist_ent_data = hist_ent_res.json()["data"]
    assert hist_ent_data["total_runs"] == 1
    assert hist_ent_data["runs"][0]["id"] == ent_data["id"]

    # 5. Run PDP Geometry (Uncalibrated)
    geom_uncal_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry",
        json={},
        headers=headers,
    )
    assert geom_uncal_res.status_code == 200
    geom_uncal = geom_uncal_res.json()["data"]
    assert geom_uncal["is_pdp_candidate"] is True
    assert geom_uncal["has_calibration"] is False
    assert geom_uncal["estimated_physical_area_sq_cm"] is None
    assert geom_uncal["status"] == "UNCALIBRATED"

    # 6. Run PDP Geometry (Calibrated)
    geom_cal_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry",
        json={"scale_px_per_mm": 5.0, "calibration_source": "TEST_MARKER"},
        headers=headers,
    )
    assert geom_cal_res.status_code == 200
    geom_cal = geom_cal_res.json()["data"]
    assert geom_cal["has_calibration"] is True
    assert geom_cal["status"] == "COMPLETED"
    assert geom_cal["estimated_physical_width_mm"] is not None
    assert geom_cal["estimated_physical_area_sq_cm"] is not None

    # 7. Retrieve historical geometry analyses
    hist_geom_res = await client.get(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry",
        headers=headers,
    )
    assert hist_geom_res.status_code == 200
    hist_geom_data = hist_geom_res.json()["data"]
    assert hist_geom_data["total_analyses"] == 2

@pytest.mark.asyncio
async def test_phase4_authorization_and_error_handling(client: AsyncClient, inspector_token: str, db_session):
    """Verify RBAC and error handling on Phase 4 endpoints."""
    headers_owner = {"Authorization": f"Bearer {inspector_token}"}

    # Setup inspection & surface
    ins_res = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Auth Test Outlet"}, headers=headers_owner)
    ins_id = ins_res.json()["data"]["id"]
    img_bytes = create_synthetic_commodity_image()
    files = {"file": ("front.png", img_bytes, "image/png")}
    up_res = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_owner)
    image_id = up_res.json()["data"]["id"]

    # Setup second inspector
    other_inspector = User(
        email=f"officer_unauth_{uuid.uuid4().hex[:6]}@metrixa.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Officer Unauthorized",
        role=UserRole.INSPECTOR,
        badge_number="LM-TEST-999",
        jurisdiction="Jaipur",
        is_active=True,
    )
    db_session.add(other_inspector)
    await db_session.commit()
    await db_session.refresh(other_inspector)
    other_token = create_access_token({"sub": str(other_inspector.id), "email": other_inspector.email, "role": other_inspector.role.value})
    headers_other = {"Authorization": f"Bearer {other_token}"}

    # Unauthorized requests receive 403
    unauth_post_ent = await client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", json={}, headers=headers_other)
    assert unauth_post_ent.status_code == 403

    unauth_get_ent = await client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", headers=headers_other)
    assert unauth_get_ent.status_code == 403

    unauth_post_geo = await client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", json={}, headers=headers_other)
    assert unauth_post_geo.status_code == 403

    unauth_get_geo = await client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", headers=headers_other)
    assert unauth_get_geo.status_code == 403

    # Non-existent inspection receives 404
    fake_id = uuid.uuid4()
    not_found_ent = await client.post(f"/api/v1/inspections/{fake_id}/images/{image_id}/entities", json={}, headers=headers_owner)
    assert not_found_ent.status_code == 404
