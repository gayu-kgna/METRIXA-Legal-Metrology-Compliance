import io
import uuid
import hashlib
import httpx
from PIL import Image, ImageDraw

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
    draw.text((30, 410), "USP: ₹ 0.50 / g", fill=(10, 10, 10))
    # Unique salt
    salt = uuid.uuid4().bytes[:3]
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    print("=== LIVE VERIFICATION: METRIXA PHASE 4 ENTITY PARSING & PDP GEOMETRY ===")

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
        assert "/api/v1/inspections/{inspection_id}/images/{image_id}/entities" in paths, "Entities route missing"
        assert "/api/v1/inspections/{inspection_id}/images/{image_id}/geometry" in paths, "Geometry route missing"
        print("[OK] OpenAPI /docs and /openapi.json contain Phase 4 entities and geometry endpoints")

        # 3. Authenticate Inspector A
        officer_email = f"officer_p4_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        password = "LiveTestPassword123!"
        reg_a = client.post("/api/v1/auth/register", json={
            "email": officer_email,
            "password": password,
            "full_name": "Inspector Sunita Rao",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-701",
            "jurisdiction": "South Delhi"
        })
        assert reg_a.status_code == 201, f"Registration failed: {reg_a.text}"

        login_a = client.post("/api/v1/auth/login", json={"email": officer_email, "password": password})
        assert login_a.status_code == 200, f"Login failed: {login_a.text}"
        token_a = login_a.json()["data"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print("[OK] Authenticated Inspector A:", officer_email)

        # 4. Create Inspection
        ins_res = client.post("/api/v1/inspections", json={
            "retail_outlet_name": "Metro Retailers Saket",
            "retail_outlet_address": "Saket District Centre, New Delhi",
            "notes": "Phase 4 Live End-to-End Verification"
        }, headers=headers_a)
        assert ins_res.status_code == 201, f"Inspection creation failed: {ins_res.text}"
        ins_id = ins_res.json()["data"]["id"]
        print("[OK] Created inspection:", ins_id)

        # 5. Upload image
        orig_bytes = create_synthetic_image()
        orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()

        files = {"file": ("front_pdp.png", orig_bytes, "image/png")}
        up_res = client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_a)
        assert up_res.status_code == 201, f"Image upload failed: {up_res.text}"
        image_id = up_res.json()["data"]["id"]
        print(f"[OK] Ingested image surface ID: {image_id} (SHA-256: {orig_sha256})")

        # 6. Run OCR
        ocr_res = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/ocr", json={
            "provider_name": "mock"
        }, headers=headers_a)
        assert ocr_res.status_code == 200, f"OCR execution failed: {ocr_res.text}"
        ocr_data = ocr_res.json()["data"]
        ocr_run_id = ocr_data["id"]
        print(f"[OK] OCR executed: run_id={ocr_run_id}, total_regions={ocr_data['total_regions_detected']}")

        # 7. Run Entity Parsing
        ent_res = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", json={
            "ocr_run_id": ocr_run_id
        }, headers=headers_a)
        assert ent_res.status_code == 200, f"Entity parsing failed: {ent_res.text}"
        ent_data = ent_res.json()["data"]
        assert ent_data["status"] == "COMPLETED"
        assert ent_data["total_entities_extracted"] > 0
        print(f"[OK] Entity Parsing executed: run_id={ent_data['id']}, entities_extracted={ent_data['total_entities_extracted']}")

        # 8. Verify Observations & Traceability
        observations = ent_data["observations"]
        obs_types = {o["field_type"]: o for o in observations}

        # Net Quantity
        assert "NET_QUANTITY" in obs_types
        q_obs = obs_types["NET_QUANTITY"]
        assert q_obs["normalized_value"]["value"] == 500.0
        assert q_obs["normalized_value"]["unit"] == "g"
        assert q_obs["normalized_value"]["base_quantity"] == 500.0
        assert len(q_obs["normalized_value"]["source_ocr_region_ids"]) >= 1
        print(f"[OK] Extracted Net Quantity: raw='{q_obs['raw_value']}', normalized={q_obs['normalized_value']['value']} {q_obs['normalized_value']['unit']}")

        # MRP
        assert "MRP" in obs_types
        mrp_obs = obs_types["MRP"]
        assert mrp_obs["normalized_value"]["value"] == 250.00
        assert mrp_obs["normalized_value"]["currency"] == "INR"
        assert mrp_obs["normalized_value"]["includes_taxes"] is True
        print(f"[OK] Extracted MRP: raw='{mrp_obs['raw_value']}', normalized=Rs.{mrp_obs['normalized_value']['value']}")

        # Date of Manufacture
        assert "DATE_OF_MANUFACTURE" in obs_types
        date_obs = obs_types["DATE_OF_MANUFACTURE"]
        assert date_obs["normalized_value"]["date_iso"] == "2026-01"
        assert date_obs["normalized_value"]["precision"] == "MONTH_YEAR"
        print(f"[OK] Extracted Date: raw='{date_obs['raw_value']}', ISO='{date_obs['normalized_value']['date_iso']}'")

        # Consumer Care
        assert "CONSUMER_CARE_PHONE" in obs_types
        assert "CONSUMER_CARE_EMAIL" in obs_types
        print(f"[OK] Extracted Consumer Care Phone & Email: {obs_types['CONSUMER_CARE_PHONE']['raw_value']}, {obs_types['CONSUMER_CARE_EMAIL']['raw_value']}")

        # Country of Origin
        assert "COUNTRY_OF_ORIGIN" in obs_types
        assert obs_types["COUNTRY_OF_ORIGIN"]["normalized_value"]["country"] == "India"
        print(f"[OK] Extracted Country of Origin: {obs_types['COUNTRY_OF_ORIGIN']['normalized_value']['country']}")

        # Legal safeguard check: verify NO PASS/FAIL verdicts returned
        for o in observations:
            assert o["status"] in ["OBSERVED", "VERIFIED", "INFERRED", "CONFLICTING", "UNKNOWN", "INDETERMINATE"]
            assert "pass" not in str(o.get("normalized_value", "")).lower()
        print("[OK] Legal Neutrality Safeguard verified: All observations are perception states without PASS/FAIL verdicts")

        # 9. Retrieve Entity History
        hist_ent = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", headers=headers_a)
        assert hist_ent.status_code == 200
        assert hist_ent.json()["data"]["total_runs"] >= 1
        print(f"[OK] Historical entity parsing runs verified: {hist_ent.json()['data']['total_runs']} run(s)")

        # 10. Run PDP Geometry (Uncalibrated)
        geo_uncal = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", json={}, headers=headers_a)
        assert geo_uncal.status_code == 200
        g_data1 = geo_uncal.json()["data"]
        assert g_data1["is_pdp_candidate"] is True
        assert g_data1["pdp_pixel_width"] == 600.0
        assert g_data1["pdp_pixel_height"] == 450.0
        assert g_data1["pdp_pixel_area"] == 270000.0
        assert g_data1["has_calibration"] is False
        assert g_data1["estimated_physical_area_sq_cm"] is None
        assert g_data1["status"] == "UNCALIBRATED"
        print(f"[OK] Uncalibrated PDP Geometry verified: pixel_area={g_data1['pdp_pixel_area']} px, physical_area=None (zero fabrication)")

        # 11. Run PDP Geometry (Calibrated)
        # Scale: 5 pixels per mm -> 600 px = 120 mm, 450 px = 90 mm -> Area = 108.0 sq cm
        geo_cal = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", json={
            "scale_px_per_mm": 5.0,
            "calibration_source": "REFERENCE_RULER_SCALE"
        }, headers=headers_a)
        assert geo_cal.status_code == 200
        g_data2 = geo_cal.json()["data"]
        assert g_data2["has_calibration"] is True
        assert g_data2["estimated_physical_width_mm"] == 120.0
        assert g_data2["estimated_physical_height_mm"] == 90.0
        assert g_data2["estimated_physical_area_sq_cm"] == 108.0
        assert g_data2["status"] == "COMPLETED"
        print(f"[OK] Calibrated PDP Geometry verified: 120.0mm x 90.0mm = {g_data2['estimated_physical_area_sq_cm']} sq cm")

        # 12. Verify Text Geometry in Declarations
        decls = g_data2["declarations_geometry"]["declarations"]
        assert len(decls) >= 1
        d_sample = decls[0]
        assert d_sample["estimated_text_height_px"] > 0
        assert d_sample["estimated_physical_text_height_mm"] > 0
        assert d_sample["quadrant"] in ["TOP_LEFT", "TOP_RIGHT", "TOP_CENTER", "CENTER", "BOTTOM_LEFT", "BOTTOM_RIGHT", "BOTTOM_CENTER", "CENTER_LEFT", "CENTER_RIGHT"]
        print(f"[OK] Text geometry verified for {d_sample['field_type']}: height={d_sample['estimated_text_height_px']}px ({d_sample['estimated_physical_text_height_mm']}mm), quadrant={d_sample['quadrant']}")

        # 13. Retrieve Geometry History
        hist_geo = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", headers=headers_a)
        assert hist_geo.status_code == 200
        assert hist_geo.json()["data"]["total_analyses"] == 2
        print(f"[OK] Historical PDP geometry runs verified: {hist_geo.json()['data']['total_analyses']} run(s)")

        # 14. RBAC Authorization Rejection for Inspector B
        officer_b_email = f"officer_b_p4_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        client.post("/api/v1/auth/register", json={
            "email": officer_b_email,
            "password": password,
            "full_name": "Inspector Anand Verma",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-702",
            "jurisdiction": "North Delhi"
        })
        login_b = client.post("/api/v1/auth/login", json={"email": officer_b_email, "password": password})
        token_b = login_b.json()["data"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        unauth_ent_post = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", json={}, headers=headers_b)
        assert unauth_ent_post.status_code == 403
        unauth_ent_get = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/entities", headers=headers_b)
        assert unauth_ent_get.status_code == 403
        unauth_geo_post = client.post(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", json={}, headers=headers_b)
        assert unauth_geo_post.status_code == 403
        unauth_geo_get = client.get(f"/api/v1/inspections/{ins_id}/images/{image_id}/geometry", headers=headers_b)
        assert unauth_geo_get.status_code == 403
        print("[OK] RBAC authorization enforcement verified: Unauthorized inspector rejected with 403 Forbidden on all Phase 4 endpoints")

    print("\n>>> ALL PHASE 4 LIVE END-TO-END VERIFICATION CHECKS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    main()
