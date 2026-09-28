import uuid
import hashlib
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_inspection_full_flow(client: AsyncClient, inspector_token: str):
    """
    Test inspection lifecycle: initialization, surface registration,
    OCR tokens, observations, and detailed aggregate retrieval.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Initialize Inspection
    ins_resp = await client.post("/api/v1/inspections", json={
        "retail_outlet_name": "Spencer's Retail Gurgaon",
        "retail_outlet_address": "MG Road, DLF Phase 2, Gurugram, Haryana",
        "geo_coordinates": {"lat": 28.4795, "lng": 77.0801, "accuracy_m": 8.5},
        "notes": "Routine packaging verification"
    }, headers=headers)
    assert ins_resp.status_code == 201
    inspection = ins_resp.json()["data"]
    ins_id = inspection["id"]

    # 2. Register Surface with SHA-256 Hash and Quality Metrics
    fake_img_bytes = b"fake_jpeg_image_data_metrixa_test"
    sha256 = hashlib.sha256(fake_img_bytes).hexdigest()
    surface_resp = await client.post("/api/v1/surfaces", json={
        "inspection_id": ins_id,
        "surface_type": "FRONT_PDP",
        "image_storage_path": "storage/inspections/surface_front_pdp.jpg",
        "sha256_hash": sha256,
        "image_width": 1920,
        "image_height": 1080,
        "file_size_bytes": len(fake_img_bytes),
        "quality_metrics": {
            "blur_laplacian_variance": 340.5,
            "glare_percentage": 1.2,
            "acceptable_for_ocr": True
        }
    }, headers=headers)
    assert surface_resp.status_code == 201
    surface = surface_resp.json()["data"]
    surface_id = surface["id"]

    # 3. Register OCR Regions (tokens and normalized coordinates)
    ocr_payload = [
        {
            "raw_text": "MRP Rs. 85.00 (INCL. OF ALL TAXES)",
            "confidence": 0.98,
            "bounding_box": {"ymin": 0.72, "xmin": 0.45, "ymax": 0.76, "xmax": 0.88},
            "token_order": 1
        },
        {
            "raw_text": "NET WT. 200 g",
            "confidence": 0.99,
            "bounding_box": {"ymin": 0.82, "xmin": 0.15, "ymax": 0.85, "xmax": 0.35},
            "token_order": 2
        }
    ]
    ocr_resp = await client.post(f"/api/v1/surfaces/{surface_id}/ocr-regions", json=ocr_payload, headers=headers)
    assert ocr_resp.status_code == 201
    ocr_regions = ocr_resp.json()["data"]
    assert len(ocr_regions) == 2

    # 4. Record Observations with Measurement Schemas
    obs_resp = await client.post("/api/v1/observations", json={
        "inspection_id": ins_id,
        "surface_id": surface_id,
        "ocr_region_id": ocr_regions[0]["id"],
        "field_type": "MRP_AMOUNT",
        "raw_value": "MRP Rs. 85.00 (INCL. OF ALL TAXES)",
        "normalized_value": {"currency": "INR", "amount": 85.00, "tax_inclusive": True},
        "source": "CAMERA_STREAM",
        "confidence": 0.98,
        "status": "OBSERVED",
        "bounding_box": {"ymin": 0.72, "xmin": 0.45, "ymax": 0.76, "xmax": 0.88},
        "package_dimensions": {"width_mm": 120.0, "height_mm": 180.0, "depth_mm": 45.0},
        "pdp_dimensions": {"area_sq_cm": 216.0, "method": "RECTANGULAR_FACE"},
        "character_height": {"estimated_height_mm": 3.2, "required_min_mm": 2.5},
        "measurement_uncertainty": {"margin_mm": 0.3}
    }, headers=headers)
    assert obs_resp.status_code == 201

    # 5. Fetch Full Inspection Detail Aggregate
    detail_resp = await client.get(f"/api/v1/inspections/{ins_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert len(detail["surfaces"]) == 1
    assert len(detail["observations"]) == 1
    assert detail["surfaces"][0]["sha256_hash"] == sha256
    assert detail["observations"][0]["field_type"] == "MRP_AMOUNT"
