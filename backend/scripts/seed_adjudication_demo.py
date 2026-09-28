import io
import os
import sys
import uuid
import httpx
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8080"

def create_demo_package_image() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (900, 650), (20, 24, 34))
    draw = ImageDraw.Draw(img)
    
    # Outer frame
    draw.rectangle([15, 15, 885, 635], outline=(6, 182, 212), width=3)
    
    # Header brand
    draw.rectangle([30, 30, 870, 90], fill=(30, 41, 59))
    draw.text((50, 45), "METRIXA SPECIAL RESERVE ORGANIC DARJEELING TEA", fill=(255, 255, 255))
    
    # Declarations section
    draw.text((50, 120), "Common Name: Black Tea (Whole Leaf)", fill=(240, 240, 240))
    draw.text((50, 170), "Manufactured & Packed by: Metrixa Agritech Pvt Ltd, Estate No. 12, Assam 781001", fill=(240, 240, 240))
    draw.text((50, 220), "NET QUANTITY: 500 g", fill=(240, 240, 240))
    draw.text((50, 270), "MAXIMUM RETAIL PRICE: Rs. 450.00 (INCL. OF ALL TAXES)", fill=(240, 240, 240))
    draw.text((50, 320), "Unit Sale Price: Rs. 0.90 per gram", fill=(240, 240, 240))
    draw.text((50, 370), "Month & Year of Manufacture: 01/2026", fill=(240, 240, 240))
    draw.text((50, 420), "Best Before 24 months from packaging date", fill=(240, 240, 240))
    draw.text((50, 470), "Consumer Care Cell: +91-1800-425-6677 | email: help@metrixa.tea", fill=(240, 240, 240))
    draw.text((50, 520), "Country of Origin: India", fill=(240, 240, 240))
    
    # Unique salt
    draw.point((5, 5), fill=(255, 255, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()

def seed_demo():
    print("=== SEEDING PHASE 8 DEMO INSPECTION FOR METRIXA ADJUDICATION CONSOLE ===")
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Check health
        h = client.get("/api/v1/health")
        assert h.status_code == 200, "Health check failed"

        # Register or login demo officer
        officer_email = "officer@metrixa.gov.in"
        officer_pwd = "Password@123"
        reg = client.post("/api/v1/auth/register", json={
            "email": officer_email,
            "password": officer_pwd,
            "full_name": "Senior Legal Metrology Inspector Sharma",
            "role": "INSPECTOR",
            "badge_number": "LM-DEL-8801",
            "jurisdiction": "Delhi NCR Central",
        })
        if reg.status_code == 201:
            print("[+] Registered demo officer:", officer_email)
        
        login_resp = client.post("/api/v1/auth/login", json={
            "email": officer_email,
            "password": officer_pwd,
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        print("[+] Logged in demo officer. Token acquired.")

        # Seed rules if not already seeded
        try:
            client.post("/api/v1/rules/seed", headers=auth_headers)
        except Exception:
            pass

        # Create demo product
        prod_resp = client.post("/api/v1/products", json={
            "brand_name": "Metrixa Organics",
            "product_name": "Reserve Darjeeling Tea 500g",
            "category": "Food & Beverages",
            "commodity_type": "Tea",
            "manufacturer_claimed": "Metrixa Agritech Pvt Ltd",
        }, headers=auth_headers)
        prod_id = prod_resp.json()["data"]["id"] if prod_resp.status_code in (200, 201) else None

        # Create inspection
        insp_resp = client.post("/api/v1/inspections", json={
            "product_id": prod_id,
            "retail_outlet_name": "HyperCity Retail Superstore, Connaught Place",
            "retail_outlet_address": "Block B, Radial Road, Connaught Place, New Delhi 110001",
            "notes": "Packaged Commodities Rule 6 statutory declaration compliance inspection",
        }, headers=auth_headers)
        assert insp_resp.status_code == 201, f"Failed to create inspection: {insp_resp.text}"
        inspection = insp_resp.json()["data"]
        insp_id = inspection["id"]
        insp_num = inspection["inspection_number"]
        print(f"[+] Created inspection: {insp_num} (ID: {insp_id})")

        # Upload Front PDP surface image
        img_bytes = create_demo_package_image()
        files = {"file": ("front_pdp.png", img_bytes, "image/png")}
        up_resp = client.post(f"/api/v1/inspections/{insp_id}/surfaces/FRONT_PDP/images", files=files, headers=auth_headers)
        assert up_resp.status_code == 201, f"Image upload failed: {up_resp.text}"
        img_id = up_resp.json()["data"]["id"]
        print(f"[+] Uploaded FRONT_PDP surface image (ID: {img_id})")

        # Run OCR
        ocr_resp = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/ocr", json={"provider_name": "mock"}, headers=auth_headers)
        print(f"[+] OCR Execution response: {ocr_resp.status_code}")
        ocr_run_id = ocr_resp.json()["data"]["id"] if ocr_resp.status_code in (200, 201) else None

        # Run Entity Extraction
        ent_resp = client.post(f"/api/v1/inspections/{insp_id}/images/{img_id}/entities", json={"ocr_run_id": ocr_run_id}, headers=auth_headers)
        print(f"[+] Entity Extraction response: {ent_resp.status_code}")

        # Evaluate Rules
        rule_resp = client.post(f"/api/v1/inspections/{insp_id}/rules/evaluate", headers=auth_headers)
        print(f"[+] Rule Evaluation response: {rule_resp.status_code}")

        # Verify Adjudication Workspace endpoint
        adj_resp = client.get(f"/api/v1/inspections/{insp_id}/adjudication", headers=auth_headers)
        assert adj_resp.status_code == 200, f"Adjudication endpoint failed: {adj_resp.text}"
        adj_data = adj_resp.json()["data"]
        print(f"[+] Adjudication Workspace State: {len(adj_data.get('regions', []))} regions, {len(adj_data.get('observations', []))} observations, {len(adj_data.get('conflicts', []))} conflict groups")

        print("\n=======================================================")
        print(f"DEMO READY FOR BROWSER WALKTHROUGH:")
        print(f"Inspection ID: {insp_id}")
        print(f"Adjudication URL: http://localhost:5173/inspections/{insp_id}/adjudication")
        print(f"Login Email:    {officer_email}")
        print(f"Login Password: {officer_pwd}")
        print("=======================================================\n")
        return insp_id

if __name__ == "__main__":
    seed_demo()
