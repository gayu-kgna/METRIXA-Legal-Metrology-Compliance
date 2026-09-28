import io
import os
import sys
import uuid
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw
from pypdf import PdfReader
from app.services.evidence.integrity import calculate_sha256

BASE_URL = "http://127.0.0.1:8080"

def create_synthetic_image() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (600, 450), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 590, 440], outline=(30, 30, 30), width=3)
    draw.text((30, 30), "METRIXA PREMIUM GREEN TEA", fill=(10, 10, 10))
    draw.text((30, 80), "Mfd By: Metrixa Foods Pvt Ltd, Plot 42, Industrial Area, New Delhi 110001", fill=(10, 10, 10))
    draw.text((30, 140), "NET QUANTITY: 500 g", fill=(10, 10, 10))
    draw.text((30, 190), "MRP Rs. 250.00 (INCL. OF ALL TAXES)", fill=(10, 10, 10))
    draw.text((30, 240), "MFG DATE: 01/2026", fill=(10, 10, 10))
    draw.text((30, 290), "CARE: 1800-111-222", fill=(10, 10, 10))
    draw.text((30, 330), "EMAIL: care@metrixa.example.com", fill=(10, 10, 10))
    draw.text((30, 370), "Country of Origin: India", fill=(10, 10, 10))
    draw.text((30, 410), "USP: Rs. 0.50 / g", fill=(10, 10, 10))
    salt = uuid.uuid4().bytes[:3]
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    print("=== LIVE VERIFICATION: METRIXA PHASE 6 EVIDENCE MANAGEMENT & EXPLAINABLE PDF DOSSIER ===")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        h = client.get("/api/v1/health")
        assert h.status_code == 200, f"Health check failed: {h.text}"
        print("[OK] Health check passed:", h.json()["data"]["database"])

        # 2. OpenAPI documentation check
        docs = client.get("/api/v1/openapi.json")
        assert docs.status_code == 200, "OpenAPI json failed"
        schema = docs.json()
        paths = schema["paths"]
        assert "/api/v1/inspections/{inspection_id}/reports" in paths, "Reports route missing"
        assert "/api/v1/inspections/{inspection_id}/reports/{report_id}/content" in paths, "Report content route missing"
        assert "/api/v1/inspections/{inspection_id}/evidence" in paths, "Evidence route missing"
        assert "/api/v1/inspections/{inspection_id}/evidence/{snapshot_id}" in paths, "Snapshot route missing"
        print("[OK] OpenAPI schema contains all Phase 6 report and evidence endpoints")

        # 3. Authenticate Inspector A
        officer_email = f"officer_p6_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        password = "LiveTestPassword123!"
        reg_a = client.post("/api/v1/auth/register", json={
            "email": officer_email,
            "password": password,
            "full_name": "Inspector Rahul Sharma",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-902",
            "jurisdiction": "South Delhi"
        })
        assert reg_a.status_code == 201, f"Registration failed: {reg_a.text}"

        login_a = client.post("/api/v1/auth/login", json={"email": officer_email, "password": password})
        assert login_a.status_code == 200, f"Login failed: {login_a.text}"
        token_a = login_a.json()["data"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print(f"[OK] Inspector A authenticated: {officer_email}")

        # 4. Create Product & Inspection
        prod_res = client.post("/api/v1/products", json={
            "brand_name": "Metrixa Green",
            "product_name": "Pure Green Tea 500g",
            "gtin_barcode": f"890{uuid.uuid4().int % 10000000000:010d}",
            "category": "Beverages",
            "commodity_type": "Tea",
        }, headers=headers_a)
        assert prod_res.status_code == 201
        prod_id = prod_res.json()["data"]["id"]

        insp_res = client.post("/api/v1/inspections", json={
            "product_id": prod_id,
            "retail_outlet_name": "Metrixa Supermart Bangalore",
            "retail_outlet_address": "Indiranagar, 100ft Road",
            "geo_coordinates": {"lat": 12.9716, "lng": 77.5946, "accuracy_m": 5.0},
        }, headers=headers_a)
        assert insp_res.status_code == 201
        insp_id = insp_res.json()["data"]["id"]
        insp_num = insp_res.json()["data"]["inspection_number"]
        print(f"[OK] Inspection created: {insp_num} (ID: {insp_id})")

        # 5. Ingest Packaging Image (FRONT_PDP)
        img_bytes = create_synthetic_image()
        files = {"file": ("front_tea.png", img_bytes, "image/png")}
        up_res = client.post(f"/api/v1/inspections/{insp_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_a)
        assert up_res.status_code == 201
        img_id = up_res.json()["data"]["id"]
        orig_img_hash = up_res.json()["data"]["sha256_hash"]
        print(f"[OK] FRONT_PDP surface ingested. Image ID: {img_id}, SHA-256: {orig_img_hash[:16]}...")

        # 6. Run OCR
        ocr_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", json={"provider_name": "mock"}, headers=headers_a)
        assert ocr_res.status_code in (200, 201)
        ocr_run_id = ocr_res.json()["data"]["id"]
        print(f"[OK] OCR executed. Run ID: {ocr_run_id}")

        # 7. Run Entity Parsing
        parse_res = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/entities", json={"ocr_run_id": ocr_run_id}, headers=headers_a)
        assert parse_res.status_code == 200
        print(f"[OK] Entity parsing completed. Extracted {parse_res.json()['data']['total_entities_extracted']} entities")

        # 8. Run PDP Geometry
        geom_res = client.post(
            f"/api/v1/inspections/{insp_id}/images/{img_id}/geometry",
            json={"reference_dimension_mm": 50.0, "reference_dimension_px": 500.0},
            headers=headers_a
        )
        assert geom_res.status_code == 200
        print(f"[OK] PDP Geometry analyzed. Status: {geom_res.json()['data']['status']}")

        # 9. Run Deterministic Legal Rule Evaluation
        eval_res = client.post(f"/api/v1/inspections/{insp_id}/rules/evaluate", json={}, headers=headers_a)
        assert eval_res.status_code == 200
        eval_summary = eval_res.json()["data"]
        print(f"[OK] Rule engine evaluated {eval_summary['total_rules']} rules. Outcomes: PASS={eval_summary['pass_count']}, FAIL={eval_summary['fail_count']}, REVIEW={eval_summary['review_count']}")

        # 10. Query Evidence Bundle
        ev_res = client.get(f"/api/v1/inspections/{insp_id}/evidence", headers=headers_a)
        assert ev_res.status_code == 200
        ev_bundle = ev_res.json()["data"]
        manifest = ev_bundle["manifest"]
        manifest_hash = ev_bundle["integrity_hash"]
        assert len(manifest_hash) == 64
        assert manifest["inspection_id"] == insp_id
        assert len(manifest["images"]) == 1
        assert manifest["images"][0]["sha256_hash"] == orig_img_hash
        print(f"[OK] Evidence Bundle retrieved. Manifest SHA-256 seal: {manifest_hash}")

        # 11. Generate Report Version 1
        rep1_res = client.post(
            f"/api/v1/inspections/{insp_id}/reports",
            json={"include_images": True, "include_ocr_dump": True},
            headers=headers_a
        )
        assert rep1_res.status_code == 201
        rep1_data = rep1_res.json()["data"]
        rep1_id = rep1_data["id"]
        rep1_hash = rep1_data["sha256_hash"]
        snap1_id = rep1_data["evidence_snapshot_id"]
        assert rep1_data["report_version"] == 1
        assert rep1_data["status"] == "GENERATED"
        print(f"[OK] Generated Dossier Report v1: Dossier ID={rep1_id}, SHA-256={rep1_hash[:16]}..., Size={rep1_data['file_size_bytes']} bytes")

        # 12. Retrieve Report Metadata
        meta_res = client.get(f"/api/v1/inspections/{insp_id}/reports/{rep1_id}", headers=headers_a)
        assert meta_res.status_code == 200
        assert meta_res.json()["data"]["id"] == rep1_id

        # 13. Download / Stream PDF Content
        content_res = client.get(f"/api/v1/inspections/{insp_id}/reports/{rep1_id}/content", headers=headers_a)
        assert content_res.status_code == 200
        assert "application/pdf" in content_res.headers["content-type"]
        assert content_res.headers["x-dossier-id"] == rep1_id
        assert content_res.headers["x-sha256-hash"] == rep1_hash
        pdf_bytes = content_res.content
        assert calculate_sha256(pdf_bytes) == rep1_hash
        print(f"[OK] Streamed PDF content matches cryptographic SHA-256 header exactly ({len(pdf_bytes)} bytes)")

        # 14. Programmatic PDF Inspection with pypdf
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        assert num_pages >= 1
        full_text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
        
        assert "METRIXA" in full_text
        assert "Legal Metrology Inspection Dossier" in full_text
        assert "LEGAL & EVIDENTIARY DISCLAIMER" in full_text
        assert "not a government-issued certificate" in full_text
        assert "1. Inspection Metadata" in full_text
        assert "2. Product Information" in full_text
        assert "3. Package Surface Overview" in full_text
        assert "4. Original Image Evidence" in full_text
        assert "5. Modular OCR Evidence" in full_text
        assert "6. Extracted Statutory Declarations" in full_text
        assert "7. Principal Display Panel (PDP) Geometry Measurements" in full_text
        assert "8. Legal Rule Evaluation Summary" in full_text
        assert "9. Detailed Rule Findings" in full_text
        assert "10. Backward Evidence Traceability Graph" in full_text
        assert "13. Cryptographic Integrity Manifest" in full_text
        assert "14. Dossier Generation Metadata" in full_text
        assert insp_num in full_text
        assert orig_img_hash[:16] in full_text
        print(f"[OK] Programmatic PDF inspection passed. Verified {num_pages} pages containing all mandatory sections, disclaimers, and hashes.")

        # 15. Generate Report Version 2 (Non-overwriting Historical Test)
        rep2_res = client.post(
            f"/api/v1/inspections/{insp_id}/reports",
            json={"include_images": False, "include_ocr_dump": False},
            headers=headers_a
        )
        assert rep2_res.status_code == 201
        rep2_data = rep2_res.json()["data"]
        rep2_id = rep2_data["id"]
        assert rep2_data["report_version"] == 2
        assert rep2_id != rep1_id

        # Verify Version 1 still retrievable and unchanged
        check_v1 = client.get(f"/api/v1/inspections/{insp_id}/reports/{rep1_id}/content", headers=headers_a)
        assert check_v1.status_code == 200
        assert calculate_sha256(check_v1.content) == rep1_hash
        print(f"[OK] Version 2 generated (ID: {rep2_id}). Version 1 remains intact with identical SHA-256 seal.")

        # 16. List Historical Reports
        hist_res = client.get(f"/api/v1/inspections/{insp_id}/reports", headers=headers_a)
        assert hist_res.status_code == 200
        reports = hist_res.json()["data"]
        assert len(reports) == 2
        assert [r["report_version"] for r in reports] == [2, 1]
        print(f"[OK] Historical reports list verified: {len(reports)} retained versions in sequence [v2, v1]")

        # 17. RBAC & Security Isolation
        unauth_email = f"unauth_officer_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        client.post("/api/v1/auth/register", json={
            "email": unauth_email,
            "password": password,
            "full_name": "Unauthorized Officer",
            "role": "INSPECTOR",
            "badge_number": "LM-MUM-999"
        })
        login_b = client.post("/api/v1/auth/login", json={"email": unauth_email, "password": password})
        assert login_b.status_code == 200, f"Login B failed: {login_b.text}"
        headers_b = {"Authorization": f"Bearer {login_b.json()['data']['access_token']}"}

        sec_get_rep = client.get(f"/api/v1/inspections/{insp_id}/reports", headers=headers_b)
        assert sec_get_rep.status_code == 403, f"Expected 403, got {sec_get_rep.status_code}"

        sec_get_content = client.get(f"/api/v1/inspections/{insp_id}/reports/{rep1_id}/content", headers=headers_b)
        assert sec_get_content.status_code == 403, f"Expected 403, got {sec_get_content.status_code}"

        sec_get_ev = client.get(f"/api/v1/inspections/{insp_id}/evidence", headers=headers_b)
        assert sec_get_ev.status_code == 403, f"Expected 403, got {sec_get_ev.status_code}"
        print("[OK] RBAC security isolation verified: Unauthorized officers correctly denied (HTTP 403)")

        # 18. Senior Adjudicator Authorized Access
        adj_email = f"adjudicator_p6_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        client.post("/api/v1/auth/register", json={
            "email": adj_email,
            "password": password,
            "full_name": "Joint Director Legal Metrology",
            "role": "ADJUDICATOR",
            "badge_number": "LM-HQ-99"
        })
        login_adj = client.post("/api/v1/auth/login", json={"email": adj_email, "password": password})
        assert login_adj.status_code == 200, f"Login Adjudicator failed: {login_adj.text}"
        headers_adj = {"Authorization": f"Bearer {login_adj.json()['data']['access_token']}"}

        adj_rep = client.get(f"/api/v1/inspections/{insp_id}/reports/{rep1_id}", headers=headers_adj)
        assert adj_rep.status_code == 200
        print("[OK] Regulatory supervisory access verified: Senior Adjudicator authorized (HTTP 200)")

    print("\n=========================================================================")
    print("ALL 18 PHASE 6 LIVE END-TO-END VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=========================================================================")

if __name__ == "__main__":
    main()
