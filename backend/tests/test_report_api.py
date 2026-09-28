import io
import uuid
import pytest
from PIL import Image, ImageDraw
from httpx import AsyncClient
from pypdf import PdfReader

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.enums import UserRole
from app.services.evidence.integrity import calculate_sha256

def create_synthetic_test_image() -> bytes:
    """Generate crisp packaging image for end-to-end integration test."""
    img = Image.new("RGB", (600, 400), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 590, 390], outline=(40, 40, 40), width=2)
    draw.text((30, 40), "METRIXA ORGANIC HONEY", fill=(0, 0, 0))
    draw.text((30, 90), "Mfd By: Metrixa Agro Products, Sector 62, Noida", fill=(0, 0, 0))
    draw.text((30, 140), "NET QUANTITY: 250 g", fill=(0, 0, 0))
    draw.text((30, 190), "MRP Rs 175.00 (INCL. OF ALL TAXES)", fill=(0, 0, 0))
    draw.text((30, 240), "MFG: 02/2026", fill=(0, 0, 0))
    draw.text((30, 290), "Customer Care: 1800-200-300", fill=(0, 0, 0))
    draw.text((30, 330), "Country of Origin: India", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.mark.asyncio
async def test_end_to_end_report_generation_and_versioning(client: AsyncClient, inspector_token: str, adjudicator_token: str):
    """
    Test complete Phase 6 pipeline:
    1. Ingestion -> OCR -> Entity Parsing -> Geometry -> Rules
    2. POST /reports generates Version 1 PDF dossier
    3. GET /reports/{id}/content streams valid PDF bytes
    4. Programmatic verification with pypdf
    5. POST /reports generates Version 2 (retaining Version 1 untouched)
    6. GET /reports lists both versions
    7. GET /evidence returns machine-readable bundle and manifest hash
    8. GET /evidence/{snapshot_id} returns snapshot metadata
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Create Inspection & Surface
    ins_res = await client.post(
        "/api/v1/inspections",
        json={"retail_outlet_name": "Phase 6 Test Retailer", "retail_outlet_address": "Bengaluru Tech Hub"},
        headers=headers,
    )
    assert ins_res.status_code == 201
    ins_id = ins_res.json()["data"]["id"]

    img_bytes = create_synthetic_test_image()
    files = {"file": ("front_honey.png", img_bytes, "image/png")}
    up_res = await client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers)
    assert up_res.status_code == 201
    img_id = up_res.json()["data"]["id"]
    orig_hash = up_res.json()["data"]["sha256_hash"]

    # 2. Run OCR, Entities, Geometry, Rules
    ocr_res = await client.post(f"/api/v1/inspections/{ins_id}/images/{img_id}/ocr", json={"provider_name": "mock"}, headers=headers)
    assert ocr_res.status_code in (200, 201)
    ocr_run_id = ocr_res.json()["data"]["id"]

    parse_res = await client.post(f"/api/v1/inspections/{ins_id}/images/{img_id}/entities", json={"ocr_run_id": ocr_run_id}, headers=headers)
    assert parse_res.status_code == 200

    geom_res = await client.post(
        f"/api/v1/inspections/{ins_id}/images/{img_id}/geometry",
        json={"reference_dimension_mm": 60.0, "reference_dimension_px": 600.0},
        headers=headers,
    )
    assert geom_res.status_code == 200

    rules_res = await client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", json={}, headers=headers)
    assert rules_res.status_code == 200
    summary = rules_res.json()["data"]
    assert summary["total_rules"] > 0

    # 3. Generate Report Version 1
    rep1_res = await client.post(
        f"/api/v1/inspections/{ins_id}/reports",
        json={"include_images": True, "include_ocr_dump": True},
        headers=headers,
    )
    assert rep1_res.status_code == 201
    rep1_data = rep1_res.json()["data"]
    assert rep1_data["report_version"] == 1
    assert rep1_data["status"] == "GENERATED"
    assert rep1_data["file_size_bytes"] > 0
    assert len(rep1_data["sha256_hash"]) == 64
    rep1_id = rep1_data["id"]
    snap1_id = rep1_data["evidence_snapshot_id"]

    # 4. Retrieve Report Version 1 Content Stream
    content1_res = await client.get(f"/api/v1/inspections/{ins_id}/reports/{rep1_id}/content", headers=headers)
    assert content1_res.status_code == 200
    assert "application/pdf" in content1_res.headers["content-type"]
    assert content1_res.headers["x-dossier-id"] == rep1_id
    assert content1_res.headers["x-sha256-hash"] == rep1_data["sha256_hash"]

    pdf_bytes_1 = content1_res.content
    assert calculate_sha256(pdf_bytes_1) == rep1_data["sha256_hash"]

    # Programmatic verification of PDF 1
    reader1 = PdfReader(io.BytesIO(pdf_bytes_1))
    assert len(reader1.pages) >= 1
    text1 = "".join(p.extract_text() or "" for p in reader1.pages)
    assert "METRIXA" in text1
    assert "Phase 6 Test Retailer" in text1
    assert orig_hash[:16] in text1
    assert "Version 1" in text1

    # 5. Generate Report Version 2
    rep2_res = await client.post(
        f"/api/v1/inspections/{ins_id}/reports",
        json={"include_images": False, "include_ocr_dump": False},
        headers=headers,
    )
    assert rep2_res.status_code == 201
    rep2_data = rep2_res.json()["data"]
    assert rep2_data["report_version"] == 2
    assert rep2_data["id"] != rep1_id  # Unique dossier ID
    rep2_id = rep2_data["id"]

    # 6. Verify Report Version 1 remains intact on disk and retrieval
    content1_check = await client.get(f"/api/v1/inspections/{ins_id}/reports/{rep1_id}/content", headers=headers)
    assert content1_check.status_code == 200
    assert calculate_sha256(content1_check.content) == rep1_data["sha256_hash"]

    # 7. List historical reports
    list_res = await client.get(f"/api/v1/inspections/{ins_id}/reports", headers=headers)
    assert list_res.status_code == 200
    reports_list = list_res.json()["data"]
    assert len(reports_list) == 2
    assert reports_list[0]["report_version"] == 2
    assert reports_list[1]["report_version"] == 1

    # 8. Query Evidence Bundle
    ev_res = await client.get(f"/api/v1/inspections/{ins_id}/evidence", headers=headers)
    assert ev_res.status_code == 200
    ev_data = ev_res.json()["data"]
    assert "manifest" in ev_data
    assert len(ev_data["integrity_hash"]) == 64
    assert ev_data["manifest"]["inspection_id"] == ins_id

    # 9. Query Specific Snapshot
    snap_res = await client.get(f"/api/v1/inspections/{ins_id}/evidence/{snap1_id}", headers=headers)
    assert snap_res.status_code == 200
    snap_data = snap_res.json()["data"]
    assert snap_data["id"] == snap1_id
    assert snap_data["application_version"] == "1.0.0"

    # 10. Senior Adjudicator access (Allowed by RBAC)
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}
    adj_res = await client.get(f"/api/v1/inspections/{ins_id}/reports/{rep1_id}", headers=adj_headers)
    assert adj_res.status_code == 200

@pytest.mark.asyncio
async def test_report_rbac_and_ownership(client: AsyncClient, inspector_token: str, db_session):
    """Verify that an unauthorized inspector receives 403 Forbidden when accessing another inspector's report."""
    headers_1 = {"Authorization": f"Bearer {inspector_token}"}

    # Inspector 1 creates inspection and generates report
    ins_res = await client.post("/api/v1/inspections", json={"retail_outlet_name": "Inspector 1 Outlet"}, headers=headers_1)
    ins_id = ins_res.json()["data"]["id"]

    rep_res = await client.post(f"/api/v1/inspections/{ins_id}/reports", json={}, headers=headers_1)
    assert rep_res.status_code == 201
    rep_id = rep_res.json()["data"]["id"]

    # Create Inspector 2
    inspector_2 = User(
        email=f"inspector2_{uuid.uuid4().hex[:6]}@metrixa.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Officer Sneha Roy",
        role=UserRole.INSPECTOR,
        is_active=True,
    )
    db_session.add(inspector_2)
    await db_session.commit()
    await db_session.refresh(inspector_2)
    inspector_2_token = create_access_token({"sub": str(inspector_2.id), "email": inspector_2.email, "role": inspector_2.role.value})
    headers_2 = {"Authorization": f"Bearer {inspector_2_token}"}

    # Inspector 2 attempts to list reports -> 403
    forbidden_list = await client.get(f"/api/v1/inspections/{ins_id}/reports", headers=headers_2)
    assert forbidden_list.status_code == 403

    # Inspector 2 attempts to get report metadata -> 403
    forbidden_get = await client.get(f"/api/v1/inspections/{ins_id}/reports/{rep_id}", headers=headers_2)
    assert forbidden_get.status_code == 403

    # Inspector 2 attempts to download PDF content -> 403
    forbidden_content = await client.get(f"/api/v1/inspections/{ins_id}/reports/{rep_id}/content", headers=headers_2)
    assert forbidden_content.status_code == 403
