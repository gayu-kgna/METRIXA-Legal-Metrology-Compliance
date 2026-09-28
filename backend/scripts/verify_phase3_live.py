import io
import uuid
import hashlib
import httpx
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:8080"

def create_synthetic_image() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (500, 350), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 490, 340], outline=(30, 30, 30), width=3)
    draw.text((30, 30), "METRIXA PREMIUM GREEN TEA", fill=(10, 10, 10))
    draw.text((30, 80), "Mfd By: Metrixa Foods Pvt Ltd, Delhi 110001", fill=(10, 10, 10))
    draw.text((30, 140), "NET QUANTITY: 500 g", fill=(10, 10, 10))
    draw.text((30, 190), "MRP Rs. 250.00 (INCL. OF ALL TAXES)", fill=(10, 10, 10))
    draw.text((30, 240), "MFG DATE: 01/2026", fill=(10, 10, 10))
    draw.text((30, 290), "CARE: 1800-111-222", fill=(10, 10, 10))
    # Unique salt
    salt = uuid.uuid4().bytes[:3]
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    print("=== LIVE VERIFICATION: METRIXA PHASE 3 OCR PIPELINE ===")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        h = client.get("/api/v1/health")
        assert h.status_code == 200, f"Health check failed: {h.text}"
        print("[OK] Health check passed:", h.json())

        # 2. OpenAPI documentation check
        docs = client.get("/api/v1/openapi.json")
        assert docs.status_code == 200, "OpenAPI json failed"
        schema = docs.json()
        paths = schema["paths"]
        assert "/api/v1/inspections/{inspection_id}/images/{image_id}/ocr" in paths, "OCR route missing in OpenAPI schema"
        print("[OK] OpenAPI /docs and /openapi.json contain Phase 3 OCR endpoints")

        # 3. Authenticate Inspector A
        officer_email = f"officer_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        password = "LiveTestPassword123!"
        reg_a = client.post("/api/v1/auth/register", json={
            "email": officer_email,
            "password": password,
            "full_name": "Inspector Vikram Malhotra",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-501",
            "jurisdiction": "Central Delhi"
        })
        assert reg_a.status_code == 201, f"Registration failed: {reg_a.text}"

        login_a = client.post("/api/v1/auth/login", json={"email": officer_email, "password": password})
        assert login_a.status_code == 200, f"Login failed: {login_a.text}"
        token_a = login_a.json()["data"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print("[OK] Authenticated Inspector A:", officer_email)

        # 4. Create Inspection
        ins_res = client.post("/api/v1/inspections", json={
            "retail_outlet_name": "Mega Mart Connaught Place",
            "retail_outlet_address": "Block B, CP, New Delhi",
            "notes": "Phase 3 Live End-to-End Verification"
        }, headers=headers_a)
        assert ins_res.status_code == 201, f"Inspection creation failed: {ins_res.text}"
        ins_id = ins_res.json()["data"]["id"]
        print("[OK] Created inspection:", ins_id)

        # 5. Upload image
        orig_bytes = create_synthetic_image()
        orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()
        print(f"[INFO] Uploading synthetic package image. SHA-256: {orig_sha256}")

        files = {"file": ("tea_box_front.png", orig_bytes, "image/png")}
        up_res = client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_a)
        assert up_res.status_code == 201, f"Image upload failed: {up_res.text}"
        image_id = up_res.json()["data"]["id"]
        print("[OK] Ingested image surface ID:", image_id)

        # 6. Run OCR Run 1: variant="original", provider="mock"
        ocr1 = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", json={
            "preprocessing_variant": "original",
            "provider_name": "mock"
        }, headers=headers_a)
        assert ocr1.status_code == 200, f"OCR Run 1 failed: {ocr1.text}"
        data1 = ocr1.json()["data"]
        run1_id = data1["id"]
        assert data1["status"] == "COMPLETED"
        assert data1["total_regions_detected"] > 0
        print(f"[OK] OCR Run 1 completed: run_id={run1_id}, regions={data1['total_regions_detected']}, chars={data1['total_characters_detected']}")

        # 7. Run OCR Run 2: variant="clahe", provider="mock"
        ocr2 = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", json={
            "preprocessing_variant": "clahe",
            "provider_name": "mock"
        }, headers=headers_a)
        assert ocr2.status_code == 200, f"OCR Run 2 failed: {ocr2.text}"
        data2 = ocr2.json()["data"]
        run2_id = data2["id"]
        assert data2["status"] == "COMPLETED"
        assert data2["processed_image_ref"] is not None
        assert "processed/" in data2["processed_image_ref"]
        print(f"[OK] OCR Run 2 completed: run_id={run2_id}, derivative={data2['processed_image_ref']}")

        # 8. Retrieve OCR history via GET
        hist = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", headers=headers_a)
        assert hist.status_code == 200, f"OCR history fetch failed: {hist.text}"
        hist_data = hist.json()["data"]
        assert hist_data["total_runs"] == 2
        assert len(hist_data["runs"]) == 2
        retrieved_run_ids = [r["id"] for r in hist_data["runs"]]
        assert run1_id in retrieved_run_ids
        assert run2_id in retrieved_run_ids
        print(f"[OK] Historical OCR runs verified: {hist_data['total_runs']} runs retained historically")

        # 9. Verify original image SHA-256 remains 100% unchanged
        content = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/content", headers=headers_a)
        assert content.status_code == 200, "Image content download failed"
        retrieved_sha = hashlib.sha256(content.content).hexdigest()
        assert retrieved_sha == orig_sha256, f"CRITICAL INTEGRITY FAILURE: {retrieved_sha} != {orig_sha256}"
        print(f"[OK] Tamper-evident verification passed: Original SHA-256 is byte-for-byte identical ({orig_sha256})")

        # 10. Verify Normalized Bounding Box Convention
        sample_reg = data1["regions"][0]
        bbox = sample_reg["bounding_box"]
        assert "x" in bbox and "y" in bbox and "width" in bbox and "height" in bbox
        assert 0.0 <= bbox["x"] <= 1.0
        assert 0.0 <= bbox["y"] <= 1.0
        assert 0.0 <= bbox["width"] <= 1.0
        assert 0.0 <= bbox["height"] <= 1.0
        print(f"[OK] Normalized bounding box verified: text='{sample_reg['raw_text']}', conf={sample_reg['confidence']}, bbox={bbox}")

        # 11. Verify Authorization (RBAC) rejection for Inspector B
        officer_b_email = f"officer_b_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        client.post("/api/v1/auth/register", json={
            "email": officer_b_email,
            "password": password,
            "full_name": "Inspector Deepa Sharma",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-502",
            "jurisdiction": "North Delhi"
        })
        login_b = client.post("/api/v1/auth/login", json={"email": officer_b_email, "password": password})
        assert login_b.status_code == 200, f"Login B failed: {login_b.text}"
        token_b = login_b.json()["data"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        unauth_post = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", json={}, headers=headers_b)
        assert unauth_post.status_code == 403, f"Expected 403 Forbidden, got {unauth_post.status_code}"

        unauth_get = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", headers=headers_b)
        assert unauth_get.status_code == 403, f"Expected 403 Forbidden, got {unauth_get.status_code}"
        print("[OK] RBAC authorization enforcement verified: Unauthorized inspector rejected with 403 Forbidden")

        # 12. Verify Tesseract provider graceful handling via API
        tess_run = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", json={
            "preprocessing_variant": "original",
            "provider_name": "tesseract"
        }, headers=headers_a)
        assert tess_run.status_code == 200
        tess_data = tess_run.json()["data"]
        assert tess_data["status"] in ["PROVIDER_UNAVAILABLE", "COMPLETED", "EMPTY"]
        print(f"[OK] Tesseract provider availability handled cleanly: status='{tess_data['status']}' (no server crash)")

    print("\n>>> ALL PHASE 3 LIVE END-TO-END VERIFICATION CHECKS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    main()
