import io
import uuid
import hashlib
import pytest
from PIL import Image, ImageDraw
from httpx import AsyncClient

from app.services.ocr.models import (
    NormalizedBoundingBox,
    RawOCRToken,
    OCRRecognitionResult,
)
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.tesseract import TesseractOCRProvider
from app.services.ocr.mock_provider import MockDeterministicOCRProvider, GOLDEN_TEST_TOKENS
from app.core.security import create_access_token
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import hash_password

def create_synthetic_commodity_image() -> bytes:
    """Create a synthetic package surface image with crisp, deterministic Legal Metrology text."""
    salt = uuid.uuid4().bytes[:4]
    bg_color = (245, 245, 245)
    img = Image.new("RGB", (600, 450), color=bg_color)
    draw = ImageDraw.Draw(img)

    draw.rectangle([10, 10, 590, 440], outline=(50, 50, 50), width=3)
    draw.text((30, 30), "METRIXA PREMIUM GREEN TEA", fill=(10, 10, 10))
    draw.text((30, 80), "Mfd By: Metrixa Foods Pvt Ltd, Plot 42, Industrial Area, New Delhi 110001", fill=(10, 10, 10))
    draw.text((30, 150), "NET QUANTITY: 500 g", fill=(10, 10, 10))
    draw.text((30, 200), "MRP Rs. 250.00 (INCL. OF ALL TAXES)", fill=(10, 10, 10))
    draw.text((30, 250), "MFG DATE: 01/2026", fill=(10, 10, 10))
    draw.text((30, 300), "CUSTOMER CARE: 1800-111-222", fill=(10, 10, 10))
    draw.text((30, 340), "EMAIL: care@metrixa.example.com", fill=(10, 10, 10))
    # Add unique pixel salt to ensure distinct SHA256 across test runs
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_ocr_provider_abstraction():
    """Verify BaseOCRProvider inheritance and contract implementation."""
    mock_prov = MockDeterministicOCRProvider()
    assert isinstance(mock_prov, BaseOCRProvider)
    assert mock_prov.is_available() is True
    assert mock_prov.name == "Mock Deterministic OCR"
    assert "synthetic" in mock_prov.version

    tess_prov = TesseractOCRProvider(tesseract_cmd="non_existent_binary_for_test")
    assert isinstance(tess_prov, BaseOCRProvider)
    assert tess_prov.name == "Tesseract OCR"

def test_tesseract_graceful_unavailability():
    """Verify Tesseract provider fails gracefully when executable is absent without crashing."""
    tess_prov = TesseractOCRProvider(tesseract_cmd="invalid_tesseract_executable_path")
    assert tess_prov.is_available() is False
    assert tess_prov.version is None

    # Call recognize when unavailable
    res = tess_prov.recognize(b"fake_image_bytes")
    assert res.status == "PROVIDER_UNAVAILABLE"
    assert res.tokens == []
    assert res.raw_text == ""
    assert "not installed" in res.error_message or "not found" in res.error_message
    assert res.duration_ms >= 0.0

def test_normalized_bounding_box_contract():
    """Verify spatial validation on NormalizedBoundingBox."""
    # Valid box
    box = NormalizedBoundingBox(x=0.1, y=0.2, width=0.5, height=0.3)
    assert box.x == 0.1
    assert box.width == 0.5

    # Out of bounds x + width > 1.0
    with pytest.raises(ValueError, match="beyond right boundary"):
        NormalizedBoundingBox(x=0.8, y=0.1, width=0.3, height=0.2)

    # Out of bounds y + height > 1.0
    with pytest.raises(ValueError, match="beyond bottom boundary"):
        NormalizedBoundingBox(x=0.1, y=0.9, width=0.2, height=0.2)

    # Safe conversion from pixel coordinates
    clamped_box = NormalizedBoundingBox.from_pixel_coords(
        x_px=100, y_px=50, width_px=300, height_px=150, img_width=500, img_height=200
    )
    assert clamped_box.x == 0.2
    assert clamped_box.y == 0.25
    assert clamped_box.width == 0.6
    assert clamped_box.height == 0.75

def test_golden_ocr_dataset_recognition():
    """Verify deterministic mock provider extracts all required Legal Metrology packaging fields."""
    provider = MockDeterministicOCRProvider()
    img_bytes = create_synthetic_commodity_image()
    res = provider.recognize(img_bytes)

    assert res.status == "COMPLETED"
    assert len(res.tokens) == len(GOLDEN_TEST_TOKENS)
    assert "METRIXA PREMIUM GREEN TEA" in res.raw_text
    assert "NET QUANTITY: 500 g" in res.raw_text
    assert "MRP Rs. 250.00" in res.raw_text
    assert "MFG DATE: 01/2026" in res.raw_text
    assert "1800-111-222" in res.raw_text
    assert "care@metrixa.example.com" in res.raw_text

    # Validate all bounding boxes obey [0, 1] normalized space
    for token in res.tokens:
        assert 0.0 <= token.bounding_box.x <= 1.0
        assert 0.0 <= token.bounding_box.y <= 1.0
        assert 0.0 <= token.bounding_box.width <= 1.0
        assert 0.0 <= token.bounding_box.height <= 1.0
        assert token.bounding_box.x + token.bounding_box.width <= 1.001
        assert token.bounding_box.y + token.bounding_box.height <= 1.001
        assert 0.0 <= token.confidence <= 1.0

def test_empty_and_failure_provider_handling():
    """Verify empty result and failure modes return controlled statuses."""
    empty_prov = MockDeterministicOCRProvider(simulate_empty=True)
    res_empty = empty_prov.recognize(b"bytes")
    assert res_empty.status == "EMPTY"
    assert res_empty.tokens == []

    fail_prov = MockDeterministicOCRProvider(simulate_failure=True)
    res_fail = fail_prov.recognize(b"bytes")
    assert res_fail.status == "FAILED"
    assert "Simulated" in res_fail.error_message

@pytest.mark.asyncio
async def test_end_to_end_ocr_api_flow(client: AsyncClient, inspector_token: str):
    """
    Verify complete image -> preprocessing -> OCR -> PostgreSQL persistence flow:
    1. Create inspection
    2. Ingest package surface image
    3. Run OCR API
    4. Validate OCRRun and OCRRegion entities
    5. Ensure original image SHA-256 remains byte-identical
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create inspection
    ins_resp = await client.post(
        "/api/v1/inspections",
        json={"retail_outlet_name": "OCR Supermarket Delhi"},
        headers=headers,
    )
    assert ins_resp.status_code == 201
    ins_id = ins_resp.json()["data"]["id"]

    # 2. Upload image
    orig_bytes = create_synthetic_commodity_image()
    orig_sha = hashlib.sha256(orig_bytes).hexdigest()

    files = {"file": ("commodity_pdp.png", orig_bytes, "image/png")}
    up_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images",
        files=files,
        headers=headers,
    )
    assert up_resp.status_code == 201
    image_id = up_resp.json()["data"]["id"]

    # 3. Run OCR with 'mock' provider and 'contrast' variant
    ocr_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"preprocessing_variant": "contrast", "provider_name": "mock"},
        headers=headers,
    )
    assert ocr_resp.status_code == 200
    run_data = ocr_resp.json()["data"]

    assert run_data["inspection_id"] == ins_id
    assert run_data["surface_id"] == image_id
    assert run_data["preprocessing_variant"] == "contrast"
    assert run_data["status"] == "COMPLETED"
    assert run_data["total_regions_detected"] > 0
    assert run_data["total_characters_detected"] > 0
    assert run_data["total_duration_ms"] > 0.0
    assert run_data["processed_image_ref"] is not None
    assert "inspections/" in run_data["processed_image_ref"]
    assert "processed/" in run_data["processed_image_ref"]

    # Check regions
    regions = run_data["regions"]
    assert len(regions) == run_data["total_regions_detected"]
    first_reg = regions[0]
    assert first_reg["ocr_run_id"] == run_data["id"]
    assert first_reg["surface_id"] == image_id
    assert 0.0 <= first_reg["confidence"] <= 1.0
    bbox = first_reg["bounding_box"]
    assert 0.0 <= bbox["x"] <= 1.0
    assert 0.0 <= bbox["y"] <= 1.0
    assert 0.0 <= bbox["width"] <= 1.0
    assert 0.0 <= bbox["height"] <= 1.0

    # 4. Verify original image binary from storage is 100% byte-for-byte unchanged
    content_resp = await client.get(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/content",
        headers=headers,
    )
    assert content_resp.status_code == 200
    assert hashlib.sha256(content_resp.content).hexdigest() == orig_sha

@pytest.mark.asyncio
async def test_multiple_ocr_runs_on_same_image(client: AsyncClient, inspector_token: str):
    """
    Verify multiple OCR runs can be executed on the same image with different variants
    and that all runs are historically preserved and retrievable.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Setup inspection & image
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Multi-OCR Mart"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    img_bytes = create_synthetic_commodity_image()
    files = {"file": ("pdp.png", img_bytes, "image/png")}
    up_resp = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers)
    image_id = up_resp.json()["data"]["id"]

    # Run 1: original variant
    run1 = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"preprocessing_variant": "original", "provider_name": "mock"},
        headers=headers,
    )
    assert run1.status_code == 200
    run1_id = run1.json()["data"]["id"]

    # Run 2: clahe variant
    run2 = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"preprocessing_variant": "clahe", "provider_name": "mock"},
        headers=headers,
    )
    assert run2.status_code == 200
    run2_id = run2.json()["data"]["id"]

    # Run 3: adaptive_threshold variant
    run3 = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"preprocessing_variant": "adaptive_threshold", "provider_name": "mock"},
        headers=headers,
    )
    assert run3.status_code == 200
    run3_id = run3.json()["data"]["id"]

    assert run1_id != run2_id != run3_id

    # Retrieve historical runs via GET
    hist_resp = await client.get(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        headers=headers,
    )
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()["data"]

    assert hist_data["surface_id"] == image_id
    assert hist_data["total_runs"] == 3
    run_ids = [r["id"] for r in hist_data["runs"]]
    assert run1_id in run_ids
    assert run2_id in run_ids
    assert run3_id in run_ids

@pytest.mark.asyncio
async def test_ocr_authorization_enforcement(client: AsyncClient, inspector_token: str, db_session):
    """Verify unauthorized officers cannot trigger or retrieve OCR for another inspector's inspection."""
    headers_owner = {"Authorization": f"Bearer {inspector_token}"}

    # Create inspection with owner
    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Secure Outlet"}, headers=headers_owner)
    ins_id = ins_resp.json()["data"]["id"]

    img_bytes = create_synthetic_commodity_image()
    files = {"file": ("pdp.png", img_bytes, "image/png")}
    up_resp = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_owner)
    image_id = up_resp.json()["data"]["id"]

    # Create second officer
    other_inspector = User(
        email=f"other_{uuid.uuid4().hex[:6]}@metrixa.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Officer Sneha Roy",
        role=UserRole.INSPECTOR,
        badge_number="LM-KOL-999",
        jurisdiction="Kolkata",
        is_active=True,
    )
    db_session.add(other_inspector)
    await db_session.commit()
    await db_session.refresh(other_inspector)
    other_token = create_access_token({"sub": str(other_inspector.id), "email": other_inspector.email, "role": other_inspector.role.value})
    headers_other = {"Authorization": f"Bearer {other_token}"}

    # Second inspector attempts to trigger OCR -> 403 Forbidden
    unauth_post = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"provider_name": "mock"},
        headers=headers_other,
    )
    assert unauth_post.status_code == 403

    # Second inspector attempts to read OCR history -> 403 Forbidden
    unauth_get = await client.get(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        headers=headers_other,
    )
    assert unauth_get.status_code == 403

@pytest.mark.asyncio
async def test_ocr_missing_image_returns_404(client: AsyncClient, inspector_token: str):
    """Verify non-existent inspection or image returns 404."""
    headers = {"Authorization": f"Bearer {inspector_token}"}
    fake_ins_id = uuid.uuid4()
    fake_img_id = uuid.uuid4()

    resp = await client.post(
        f"/api/v1/inspections/{fake_ins_id}/images/{fake_img_id}/ocr",
        json={"provider_name": "mock"},
        headers=headers,
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_tesseract_api_graceful_handling(client: AsyncClient, inspector_token: str):
    """
    Verify triggering OCR with tesseract provider in environment without tesseract
    returns controlled PROVIDER_UNAVAILABLE status without crashing the API.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    ins_resp = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Tesseract Test Store"}, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    img_bytes = create_synthetic_commodity_image()
    files = {"file": ("pdp.png", img_bytes, "image/png")}
    up_resp = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers)
    image_id = up_resp.json()["data"]["id"]

    ocr_resp = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr",
        json={"preprocessing_variant": "original", "provider_name": "tesseract"},
        headers=headers,
    )
    assert ocr_resp.status_code == 200
    run_data = ocr_resp.json()["data"]
    # In an environment without tesseract, status is PROVIDER_UNAVAILABLE; if installed, COMPLETED.
    assert run_data["status"] in ["PROVIDER_UNAVAILABLE", "COMPLETED", "EMPTY"]
    assert run_data["provider_name"] == "Tesseract OCR"
