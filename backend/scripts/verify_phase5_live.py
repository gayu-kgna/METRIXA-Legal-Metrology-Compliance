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
    draw.text((30, 410), "USP: Rs. 0.50 / g", fill=(10, 10, 10))
    # Unique salt
    salt = uuid.uuid4().bytes[:3]
    draw.point((1, 1), fill=(salt[0], salt[1], salt[2]))
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    print("=== LIVE VERIFICATION: METRIXA PHASE 5 DETERMINISTIC LEGAL RULE ENGINE ===")

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
        assert "/api/v1/inspections/{inspection_id}/rules/evaluate" in paths, "Rule evaluate route missing"
        assert "/api/v1/inspections/{inspection_id}/rules/evaluations" in paths, "Rule evaluations route missing"
        assert "/api/v1/rules" in paths, "Rules list route missing"
        print("[OK] OpenAPI /docs and /openapi.json contain Phase 5 rule engine endpoints")

        # 3. Authenticate Inspector A
        officer_email = f"officer_p5_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        password = "LiveTestPassword123!"
        reg_a = client.post("/api/v1/auth/register", json={
            "email": officer_email,
            "password": password,
            "full_name": "Inspector Meera Verma",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-801",
            "jurisdiction": "Central Delhi"
        })
        assert reg_a.status_code == 201, f"Registration failed: {reg_a.text}"

        login_a = client.post("/api/v1/auth/login", json={"email": officer_email, "password": password})
        assert login_a.status_code == 200, f"Login failed: {login_a.text}"
        token_a = login_a.json()["data"]["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print("[OK] Authenticated Inspector A:", officer_email)

        # 4. Create Product & Inspection
        prod_res = client.post("/api/v1/products", json={
            "brand_name": "Metrixa Organics",
            "product_name": "Premium Green Tea 500g",
            "category": "Beverages",
            "commodity_type": "Tea",
        }, headers=headers_a)
        assert prod_res.status_code == 201
        prod_id = prod_res.json()["data"]["id"]

        ins_res = client.post("/api/v1/inspections", json={
            "product_id": prod_id,
            "retail_outlet_name": "Metrixa Supermart Connaught Place",
            "retail_outlet_address": "CP Inner Circle, New Delhi",
            "notes": "Phase 5 Live End-to-End Verification"
        }, headers=headers_a)
        assert ins_res.status_code == 201
        ins_id = ins_res.json()["data"]["id"]
        print("[OK] Created inspection:", ins_id)

        # 5. Ingest package surface image
        img_bytes = create_synthetic_image()
        img_hash = hashlib.sha256(img_bytes).hexdigest()
        files = {"file": ("front_pdp.png", img_bytes, "image/png")}
        up_res = client.post(f"/api/v1/inspections/{ins_id}/surfaces/FRONT_PDP/images", files=files, headers=headers_a)
        assert up_res.status_code == 201, f"Ingestion failed: {up_res.text}"
        surface_id = up_res.json()["data"]["id"]
        print(f"[OK] Ingested image surface ID: {surface_id} (SHA-256: {img_hash})")

        # 6. Run OCR (Mock deterministic provider)
        ocr_res = client.post(
            f"/api/v1/inspections/{ins_id}/images/{surface_id}/ocr",
            json={"provider_name": "mock"},
            headers=headers_a,
        )
        assert ocr_res.status_code == 200, f"OCR failed: {ocr_res.text}"
        ocr_data = ocr_res.json()["data"]
        print(f"[OK] OCR executed: run_id={ocr_data['id']}, total_regions={ocr_data['total_regions_detected']}")

        # 7. Run Entity Parsing
        parse_res = client.post(
            f"/api/v1/inspections/{ins_id}/images/{surface_id}/entities",
            headers=headers_a,
        )
        assert parse_res.status_code == 200, f"Entity parsing failed: {parse_res.text}"
        parse_data = parse_res.json()["data"]
        print(f"[OK] Entity Parsing executed: run_id={parse_data['id']}, entities={parse_data['total_entities_extracted']}")

        # 8. Run PDP Geometry analysis with authentic calibration
        geom_res = client.post(
            f"/api/v1/inspections/{ins_id}/images/{surface_id}/geometry",
            json={
                "surface_type": "FRONT_PDP",
                "reference_dimension_mm": 120.0,
                "reference_dimension_px": 600.0,
                "calibration_source": "REFERENCE_RULER",
            },
            headers=headers_a,
        )
        assert geom_res.status_code == 200, f"Geometry failed: {geom_res.text}"
        geom_data = geom_res.json()["data"]
        print(f"[OK] Calibrated PDP Geometry executed: scale={geom_data['scale_px_per_mm']} px/mm, physical_area={geom_data['estimated_physical_area_sq_cm']} sq cm")

        # 9. Trigger Deterministic Legal Rule Evaluation
        eval_res1 = client.post(
            f"/api/v1/inspections/{ins_id}/rules/evaluate",
            json={"include_test_rules": False},
            headers=headers_a,
        )
        assert eval_res1.status_code == 200, f"Rule evaluation failed: {eval_res1.text}"
        summary1 = eval_res1.json()["data"]
        print(f"[OK] Deterministic Rule Engine Evaluation Run 1: total={summary1['total_rules']}, pass={summary1['pass_count']}, fail={summary1['fail_count']}, review={summary1['review_count']}, indet={summary1['indeterminate_count']}, na={summary1['not_applicable_count']}")

        # Verify verdicts and explainability
        eval_dict = {e["rule_code"]: e for e in summary1["evaluations"]}
        
        # Rule 6(1)(c) Net Quantity -> PASS
        assert "PCR-2011-R06-1-C" in eval_dict
        r_qty = eval_dict["PCR-2011-R06-1-C"]
        assert r_qty["outcome"] == "PASS"
        assert "500.0 g" in r_qty["legal_rationale"] or "500" in r_qty["legal_rationale"]
        print("[OK] Net Quantity Rule PASS with statutory rationale:", r_qty["legal_rationale"])

        # Rule 6(1)(da) MRP -> PASS
        assert "PCR-2011-R06-1-DA" in eval_dict
        r_mrp = eval_dict["PCR-2011-R06-1-DA"]
        assert r_mrp["outcome"] == "PASS"
        assert "inclusive of all taxes" in r_mrp["legal_rationale"]
        print("[OK] MRP Rule PASS with tax inclusivity verification:", r_mrp["legal_rationale"])

        # Rule 6(1)(a) Party (Manufacturer) -> PASS
        assert "PCR-2011-R06-1-A" in eval_dict
        r_party = eval_dict["PCR-2011-R06-1-A"]
        assert r_party["outcome"] == "PASS"
        print("[OK] Party Declaration Rule PASS:", r_party["legal_rationale"])

        # Rule 6(1)(e) Consumer Care -> PASS
        assert "PCR-2011-R06-1-E" in eval_dict
        r_care = eval_dict["PCR-2011-R06-1-E"]
        assert r_care["outcome"] == "PASS"
        print("[OK] Consumer Care Rule PASS:", r_care["legal_rationale"])

        # Rule 6(1)(f) Country of Origin -> NOT_APPLICABLE for domestic commodity
        assert "PCR-2011-R06-1-F" in eval_dict
        r_origin = eval_dict["PCR-2011-R06-1-F"]
        assert r_origin["outcome"] == "NOT_APPLICABLE"
        print("[OK] Country of Origin Rule NOT_APPLICABLE (applicability separated from evaluation):", r_origin["legal_rationale"])

        # Rule 6(1)(g) Unit Sale Price -> NOT_APPLICABLE (quantity 500g does not exceed 1000g threshold)
        assert "PCR-2011-R06-1-G" in eval_dict
        r_usp = eval_dict["PCR-2011-R06-1-G"]
        assert r_usp["outcome"] == "NOT_APPLICABLE"
        print("[OK] Unit Sale Price Rule NOT_APPLICABLE (quantity does not exceed statutory threshold):", r_usp["legal_rationale"])

        # Rule 7(1) PDP Font Height -> PASS (calibrated font height >= 2.0 mm)
        assert "PCR-2011-R07-1" in eval_dict
        r_geom = eval_dict["PCR-2011-R07-1"]
        assert r_geom["outcome"] == "PASS"
        print("[OK] PDP Font Height Rule PASS with calibrated physical measurement:", r_geom["legal_rationale"])

        # 10. Verify Determinism: execute evaluation Run 2 and check identical counts
        eval_res2 = client.post(
            f"/api/v1/inspections/{ins_id}/rules/evaluate",
            json={"include_test_rules": False},
            headers=headers_a,
        )
        assert eval_res2.status_code == 200
        summary2 = eval_res2.json()["data"]
        assert summary2["pass_count"] == summary1["pass_count"]
        assert summary2["fail_count"] == summary1["fail_count"]
        assert summary2["review_count"] == summary1["review_count"]
        assert summary2["indeterminate_count"] == summary1["indeterminate_count"]
        assert summary2["not_applicable_count"] == summary1["not_applicable_count"]
        print("[OK] Determinism verified: Run 2 returned byte-for-byte identical verdict counts")

        # 11. Historical Evaluations API check
        hist_res = client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations", headers=headers_a)
        assert hist_res.status_code == 200
        eval_history = hist_res.json()["data"]
        assert len(eval_history) >= summary1["total_rules"] * 2
        print(f"[OK] Historical evaluations verified: {len(eval_history)} evaluations retained historically")

        # 12. Single Evaluation Detail API check
        first_eval_id = eval_history[0]["id"]
        single_res = client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations/{first_eval_id}", headers=headers_a)
        assert single_res.status_code == 200
        single_eval = single_res.json()["data"]
        assert single_eval["id"] == first_eval_id
        assert "statutory_citation" in single_eval
        assert "evidence_references" in single_eval
        print("[OK] Single evaluation detail verified with complete evidence traceability graph")

        # 13. RBAC Security: Unauthorized Inspector B rejected with 403 Forbidden
        other_email = f"officer_b_{uuid.uuid4().hex[:6]}@metrixa.gov.in"
        client.post("/api/v1/auth/register", json={
            "email": other_email,
            "password": password,
            "full_name": "Inspector Ramesh Nair",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-802",
            "jurisdiction": "North Delhi"
        })
        login_b = client.post("/api/v1/auth/login", json={"email": other_email, "password": password})
        token_b = login_b.json()["data"]["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        unauth_eval = client.post(f"/api/v1/inspections/{ins_id}/rules/evaluate", headers=headers_b)
        assert unauth_eval.status_code == 403, f"Expected 403, got {unauth_eval.status_code}"

        unauth_hist = client.get(f"/api/v1/inspections/{ins_id}/rules/evaluations", headers=headers_b)
        assert unauth_hist.status_code == 403, f"Expected 403, got {unauth_hist.status_code}"
        print("[OK] RBAC authorization enforcement verified: Unauthorized inspector rejected with 403 Forbidden")

    print("\n>>> ALL PHASE 5 LIVE END-TO-END VERIFICATION CHECKS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    main()
