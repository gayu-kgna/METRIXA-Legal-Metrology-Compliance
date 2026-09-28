import io
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8080"

def create_synthetic_image(text: str, color=(240, 240, 240)) -> bytes:
    img = Image.new("RGB", (640, 480), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 630, 470], outline=(100, 100, 100), width=3)
    draw.text((30, 40), f"METRIXA STATUTORY EVIDENCE: {text}", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def seed_phase9_demo():
    print("=== SEEDING PHASE 9 PRODUCT LEDGER & TIMELINE DEMO ===")
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Auth demo officer
        officer_email = "officer@metrixa.gov.in"
        officer_pwd = "Password@123"
        login_resp = client.post("/api/v1/auth/login", json={"email": officer_email, "password": officer_pwd})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Register or find Flagship Product
        gtin = "8901234567890"
        prod_check = client.get(f"/api/v1/products?gtin={gtin}", headers=headers).json()
        product_id = None
        if prod_check.get("data") and len(prod_check["data"]) > 0:
            product_id = prod_check["data"][0]["id"]
            print(f"[+] Found existing demo product: {product_id}")
        else:
            prod_resp = client.post(
                "/api/v1/products",
                json={
                    "brand_name": "Himalayan Gold",
                    "product_name": "Organic Darjeeling Green Tea 250g",
                    "category": "Beverages & Tea",
                    "commodity_type": "Pre-packaged Tea Leaves",
                    "gtin_barcode": gtin,
                    "manufacturer_claimed": "Himalayan Tea Estates Ltd, Darjeeling, West Bengal",
                    "metadata_json": {
                        "standards": "PCR_2011_SCHEDULE_2",
                        "intended_use": "Direct Consumption",
                    }
                },
                headers=headers
            )
            assert prod_resp.status_code in (201, 200), f"Product creation failed: {prod_resp.text}"
            product_id = prod_resp.json()["data"]["id"]
            print(f"[+] Registered flagship product: {product_id}")

        # 2. Check or create Baseline Inspection (Inspection 1, v1.0)
        insp1_resp = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product_id,
                "retail_outlet_name": "Modern Bazaar, Connaught Place",
                "retail_outlet_address": "Block B, Connaught Place, New Delhi 110001",
                "notes": "Baseline enforcement check for packaging compliance",
            },
            headers=headers
        )
        assert insp1_resp.status_code == 201
        insp1_id = insp1_resp.json()["data"]["id"]
        print(f"[+] Created Baseline Inspection: {insp1_id}")

        # Ingest PDP image for Inspection 1
        img1 = create_synthetic_image("Himalayan Gold Green Tea v1.0 Baseline")
        up1 = client.post(
            f"/api/v1/inspections/{insp1_id}/surfaces/FRONT_PDP/images",
            files={"file": ("front_pdp.jpg", img1, "image/jpeg")},
            headers=headers
        )
        assert up1.status_code == 201, f"Image 1 upload failed: {up1.text}"

        # Baseline Label Version 1.0 declarations
        decl_v1 = {
            "MRP": "Rs. 450.00",
            "NET_QUANTITY": "250 g",
            "MANUFACTURER_NAME": "Himalayan Tea Estates Ltd",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "care@himalayantea.in",
            "DATE_OF_MANUFACTURE": "01/2026",
            "UNIT_SALE_PRICE": "Rs. 1.80 / g",
            "GENERIC_NAME": "Organic Green Tea",
        }

        # Add observations
        for ftype, val in decl_v1.items():
            client.post(
                f"/api/v1/inspections/{insp1_id}/observations/manual",
                json={
                    "field_type": ftype,
                    "raw_value": val,
                    "normalized_value": {"formatted": val},
                    "reason": "Baseline inspection observation",
                },
                headers=headers
            )

        # Evaluate rules and generate report for Inspection 1
        client.post(f"/api/v1/inspections/{insp1_id}/rules/re-evaluate", json={"justification": "Initial compliance run"}, headers=headers)
        client.post(f"/api/v1/inspections/{insp1_id}/reports", json={"report_type": "SUMMARY_VERIFICATION_CERTIFICATE"}, headers=headers)

        # 3. Create Second Inspection (Inspection 2, Label Revision v2.0)
        insp2_resp = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product_id,
                "retail_outlet_name": "Spencer's Retail, Cyber City",
                "retail_outlet_address": "DLF Cyber City, Sector 24, Gurgaon 122002",
                "notes": "Follow-up surveillance inspection observing revised price and contact imprint",
            },
            headers=headers
        )
        assert insp2_resp.status_code == 201
        insp2_id = insp2_resp.json()["data"]["id"]
        print(f"[+] Created Follow-up Inspection: {insp2_id}")

        img2 = create_synthetic_image("Himalayan Gold Green Tea v2.0 Revised")
        up2 = client.post(
            f"/api/v1/inspections/{insp2_id}/surfaces/FRONT_PDP/images",
            files={"file": ("front_pdp.jpg", img2, "image/jpeg")},
            headers=headers
        )
        assert up2.status_code == 201, f"Image 2 upload failed: {up2.text}"

        # Revised Label Version 2.0 declarations (MRP increased to 490, email updated, expiry added)
        decl_v2 = {
            "MRP": "Rs. 490.00",
            "NET_QUANTITY": "250 g",
            "MANUFACTURER_NAME": "Himalayan Tea Estates Ltd",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "support@himalayantea.in",
            "DATE_OF_MANUFACTURE": "08/2026",
            "EXPIRY_DATE": "08/2027",
            "UNIT_SALE_PRICE": "Rs. 1.96 / g",
            "GENERIC_NAME": "Organic Green Tea",
        }

        for ftype, val in decl_v2.items():
            obs_resp = client.post(
                f"/api/v1/inspections/{insp2_id}/observations/manual",
                json={
                    "field_type": ftype,
                    "raw_value": val,
                    "normalized_value": {"formatted": val},
                    "reason": "Observed on revised packaging artwork",
                },
                headers=headers
            )
            # Adjudicate one observation to verify
            if ftype == "MRP" and obs_resp.status_code == 201:
                obs_id = obs_resp.json()["data"]["id"]
                client.post(
                    f"/api/v1/inspections/{insp2_id}/observations/{obs_id}/verify",
                    json={"notes": "Officer verified price tag on physical package sample"},
                    headers=headers
                )

        client.post(f"/api/v1/inspections/{insp2_id}/rules/re-evaluate", json={"justification": "Adjudicated revised label run"}, headers=headers)
        client.post(f"/api/v1/inspections/{insp2_id}/reports", json={"report_type": "DETAILED_TECHNICAL_DOSSIER"}, headers=headers)

        # 4. Resolve label versions in backend service
        from app.services.product.ledger_service import resolve_or_create_label_version
        from app.core.database import AsyncSessionLocal
        import asyncio

        async def record_versions():
            async with AsyncSessionLocal() as db:
                v1 = await resolve_or_create_label_version(db, uuid.UUID(product_id), uuid.UUID(insp1_id), decl_v1, notes="Baseline artwork")
                v2 = await resolve_or_create_label_version(db, uuid.UUID(product_id), uuid.UUID(insp2_id), decl_v2, notes="Revision with updated MRP & Consumer Care")
                print(f"[+] Label versions resolved: {v1.version_tag} (fingerprint: {v1.version_fingerprint[:16]}...) and {v2.version_tag} (fingerprint: {v2.version_fingerprint[:16]}...)")

        asyncio.run(record_versions())

        print(f"\n[SUCCESS] Phase 9 Demo Seeded successfully! Product ID: {product_id}\n")
        return product_id

if __name__ == "__main__":
    seed_phase9_demo()
