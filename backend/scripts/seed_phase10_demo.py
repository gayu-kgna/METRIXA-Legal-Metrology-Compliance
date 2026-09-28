import io
import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import httpx
from PIL import Image, ImageDraw

# Add backend to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get("METRIXA_BASE_URL", "http://127.0.0.1:8080")

def create_synthetic_package_image(title: str, subtitle: str, color=(240, 245, 250)) -> bytes:
    img = Image.new("RGB", (800, 600), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, 785, 585], outline=(60, 70, 90), width=4)
    draw.rectangle([25, 25, 775, 95], fill=(30, 45, 75))
    draw.text((40, 45), f"METRIXA STATUTORY EVIDENCE SNAPSHOT", fill=(255, 255, 255))
    draw.text((40, 120), title.upper(), fill=(20, 30, 50))
    draw.text((40, 160), subtitle, fill=(80, 90, 110))
    draw.text((40, 220), "Legal Metrology (Packaged Commodities) Rules, 2011", fill=(100, 110, 130))
    draw.text((40, 260), f"Digital Evidence Salt: {uuid.uuid4().hex[:12]}", fill=(140, 150, 170))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

def seed_phase10_demo():
    print("\n" + "=" * 80)
    print(" METRIXA SIH 2026 DEMO PACKAGING SEEDER")
    print(" Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011")
    print("=" * 80 + "\n")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Authenticate Demo Officer
        officer_email = "officer@metrixa.gov.in"
        officer_pwd = "Password@123"
        print(f"[*] Authenticating demo officer: {officer_email}...")
        login_resp = client.post("/api/v1/auth/login", json={"email": officer_email, "password": officer_pwd})
        if login_resp.status_code != 200:
            print(f"[!] Primary officer login failed. Attempting inspector fallback...")
            login_resp = client.post("/api/v1/auth/login", json={"email": "inspector@metrixa.gov.in", "password": "InspectorPass123!"})
        
        assert login_resp.status_code == 200, f"Authentication failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[+] Authentication successful.")

        # =====================================================================
        # SCENARIO 1: Flagship Product Ledger & Shrinkflation / Timeline
        # "Himalayan Gold Organic Green Tea" (GTIN: 8901234567890)
        # =====================================================================
        print("\n--- [Scenario 1] Seeding Product Ledger & Label Version Evolution ---")
        gtin1 = "8901234567890"
        prod1_resp = client.get(f"/api/v1/products?gtin={gtin1}", headers=headers).json()
        product1_id = None
        if prod1_resp.get("data") and len(prod1_resp["data"]) > 0:
            product1_id = prod1_resp["data"][0]["id"]
            print(f"[+] Found existing flagship product: {product1_id}")
        else:
            p1 = client.post(
                "/api/v1/products",
                json={
                    "brand_name": "Himalayan Gold",
                    "product_name": "Organic Darjeeling Green Tea 250g",
                    "category": "Beverages & Tea",
                    "commodity_type": "Pre-packaged Tea Leaves",
                    "gtin_barcode": gtin1,
                    "manufacturer_claimed": "Himalayan Tea Estates Ltd, Darjeeling, West Bengal",
                    "metadata_json": {"standards": "PCR_2011_SCHEDULE_2"}
                },
                headers=headers
            )
            product1_id = p1.json()["data"]["id"]
            print(f"[+] Registered flagship product: {product1_id}")

        # Inspection 1A: Baseline Inspection (Compliant v1.0)
        ins1a = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product1_id,
                "retail_outlet_name": "Modern Bazaar, Connaught Place",
                "retail_outlet_location": "Block B, Connaught Place, New Delhi 110001",
                "notes": "Baseline enforcement check for packaging compliance (Version 1.0)",
            },
            headers=headers
        ).json()["data"]
        ins1a_id = ins1a["id"]
        print(f"  [+] Baseline Inspection 1A created: {ins1a_id}")

        img1a = create_synthetic_package_image("Himalayan Gold Green Tea", "250g Net Qty | Rs. 250.00 MRP (v1.0)")
        client.post(
            f"/api/v1/inspections/{ins1a_id}/surfaces/FRONT_PDP/images",
            files={"file": ("front_v1.jpg", img1a, "image/jpeg")},
            headers=headers
        )

        obs_v1 = [
            ("BRAND_NAME", "Himalayan Gold", {"value": "Himalayan Gold"}),
            ("PRODUCT_NAME", "Organic Darjeeling Green Tea 250g", {"value": "Organic Darjeeling Green Tea 250g"}),
            ("NET_QUANTITY", "250 g", {"value": 250.0, "unit": "g"}),
            ("MRP", "Rs. 250.00 (incl. of all taxes)", {"value": 250.0, "currency": "INR", "includes_taxes": True}),
            ("UNIT_SALE_PRICE", "Rs. 1.00 / g", {"value": 1.00, "unit": "g"}),
            ("DATE_OF_PACKING", "10/2025", {"date_iso": "2025-10"}),
            ("MANUFACTURER_NAME", "Himalayan Tea Estates Ltd, Darjeeling", {"name": "Himalayan Tea Estates Ltd"}),
            ("COUNTRY_OF_ORIGIN", "India", {"country": "India"}),
            ("CONSUMER_CARE_EMAIL", "care@himalayangold.in", {"emails": ["care@himalayangold.in"]}),
        ]
        for ftype, raw, norm in obs_v1:
            client.post(
                "/api/v1/observations",
                json={
                    "inspection_id": ins1a_id,
                    "field_type": ftype,
                    "raw_value": raw,
                    "normalized_value": norm,
                    "source": "OFFICER_INPUT",
                    "status": "VERIFIED",
                    "confidence": 0.98,
                },
                headers=headers
            )
        client.post(f"/api/v1/inspections/{ins1a_id}/rules/evaluate", json={}, headers=headers)
        client.post(f"/api/v1/inspections/{ins1a_id}/reports", json={"include_images": True}, headers=headers)

        # Inspection 1B: Follow-up Inspection (Changed Label v2.0 - Shrinkflation)
        ins1b = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product1_id,
                "retail_outlet_name": "Spencer's Retail, Gurgaon",
                "retail_outlet_location": "Mall Mile, MG Road, Gurugram 122002",
                "notes": "Follow-up enforcement check; label version change detected (Version 2.0)",
            },
            headers=headers
        ).json()["data"]
        ins1b_id = ins1b["id"]
        print(f"  [+] Follow-up Inspection 1B created: {ins1b_id}")

        img1b = create_synthetic_package_image("Himalayan Gold Green Tea", "220g Net Qty | Rs. 280.00 MRP (v2.0 Revision)")
        client.post(
            f"/api/v1/inspections/{ins1b_id}/surfaces/FRONT_PDP/images",
            files={"file": ("front_v2.jpg", img1b, "image/jpeg")},
            headers=headers
        )

        obs_v2 = [
            ("BRAND_NAME", "Himalayan Gold", {"value": "Himalayan Gold"}),
            ("PRODUCT_NAME", "Organic Darjeeling Green Tea 220g", {"value": "Organic Darjeeling Green Tea 220g"}),
            ("NET_QUANTITY", "220 g", {"value": 220.0, "unit": "g"}),  # Shrinkflation: 250g -> 220g
            ("MRP", "Rs. 280.00 (incl. of all taxes)", {"value": 280.0, "currency": "INR", "includes_taxes": True}),  # Price rise
            ("UNIT_SALE_PRICE", "Rs. 1.27 / g", {"value": 1.27, "unit": "g"}),
            ("DATE_OF_PACKING", "02/2026", {"date_iso": "2026-02"}),
            ("MANUFACTURER_NAME", "Himalayan Tea Estates Ltd, Darjeeling", {"name": "Himalayan Tea Estates Ltd"}),
            ("COUNTRY_OF_ORIGIN", "India", {"country": "India"}),
            ("CONSUMER_CARE_EMAIL", "care@himalayangold.in", {"emails": ["care@himalayangold.in"]}),
        ]
        for ftype, raw, norm in obs_v2:
            client.post(
                "/api/v1/observations",
                json={
                    "inspection_id": ins1b_id,
                    "field_type": ftype,
                    "raw_value": raw,
                    "normalized_value": norm,
                    "source": "OFFICER_INPUT",
                    "status": "VERIFIED",
                    "confidence": 0.98,
                },
                headers=headers
            )
        client.post(f"/api/v1/inspections/{ins1b_id}/rules/evaluate", json={}, headers=headers)
        client.post(f"/api/v1/inspections/{ins1b_id}/reports", json={"include_images": True}, headers=headers)

        # =====================================================================
        # SCENARIO 2: Live Human Adjudication (Conflicting Dual MRP)
        # "Royal Basmati Reserve 1kg" (GTIN: 8908765432109)
        # =====================================================================
        print("\n--- [Scenario 2] Seeding Live Adjudication Demo (Dual Pricing Conflict) ---")
        gtin2 = "8908765432109"
        p2 = client.post(
            "/api/v1/products",
            json={
                "brand_name": "Royal Basmati Reserve",
                "product_name": "Aged Long Grain Basmati Rice 1kg",
                "category": "Grains & Cereals",
                "commodity_type": "Milled Rice",
                "gtin_barcode": gtin2,
                "manufacturer_claimed": "Royal Rice Mills Ltd, Karnal, Haryana",
            },
            headers=headers
        )
        product2_id = p2.json()["data"]["id"] if p2.status_code == 201 else client.get(f"/api/v1/products?gtin={gtin2}", headers=headers).json()["data"][0]["id"]
        print(f"[+] Product 2 registered: {product2_id}")

        ins2 = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product2_id,
                "retail_outlet_name": "BigBazaar Hypermarket, Noida",
                "retail_outlet_location": "Sector 18, Noida 201301",
                "notes": "Suspected retail dual pricing; sticker pasted over statutory MRP",
            },
            headers=headers
        ).json()["data"]
        ins2_id = ins2["id"]
        print(f"  [+] Adjudication Inspection 2 created: {ins2_id}")

        img2 = create_synthetic_package_image("Royal Basmati Reserve", "Dual Price Overprint: Factory Rs. 180 vs Sticker Rs. 210")
        client.post(
            f"/api/v1/inspections/{ins2_id}/surfaces/FRONT_PDP/images",
            files={"file": ("dual_mrp.jpg", img2, "image/jpeg")},
            headers=headers
        )

        obs_dual = [
            ("BRAND_NAME", "Royal Basmati Reserve", {"value": "Royal Basmati Reserve"}, "VERIFIED"),
            ("PRODUCT_NAME", "Aged Long Grain Basmati Rice 1kg", {"value": "Aged Long Grain Basmati Rice 1kg"}, "VERIFIED"),
            ("NET_QUANTITY", "1 kg", {"value": 1.0, "unit": "kg"}, "VERIFIED"),
            ("MRP", "Rs. 180.00 (incl. of all taxes)", {"value": 180.0, "currency": "INR", "includes_taxes": True}, "OBSERVED"),
            ("MRP", "Rs. 210.00", {"value": 210.0, "currency": "INR", "includes_taxes": False}, "CONFLICTING"),
            ("UNIT_SALE_PRICE", "Rs. 180.00 / kg", {"value": 180.0, "unit": "kg"}, "VERIFIED"),
            ("DATE_OF_PACKING", "01/2026", {"date_iso": "2026-01"}, "VERIFIED"),
            ("MANUFACTURER_NAME", "Royal Rice Mills Ltd, Karnal", {"name": "Royal Rice Mills Ltd"}, "VERIFIED"),
            ("COUNTRY_OF_ORIGIN", "India", {"country": "India"}, "VERIFIED"),
            ("CONSUMER_CARE_EMAIL", "care@royalrice.in", {"emails": ["care@royalrice.in"]}, "VERIFIED"),
        ]
        for ftype, raw, norm, status_val in obs_dual:
            client.post(
                "/api/v1/observations",
                json={
                    "inspection_id": ins2_id,
                    "field_type": ftype,
                    "raw_value": raw,
                    "normalized_value": norm,
                    "source": "OFFICER_INPUT" if status_val == "VERIFIED" else "CAMERA_STREAM",
                    "status": status_val,
                    "confidence": 0.94 if status_val != "CONFLICTING" else 0.88,
                },
                headers=headers
            )
        # Evaluate rules so it shows REVIEW / Non-compliant pending adjudication
        client.post(f"/api/v1/inspections/{ins2_id}/rules/evaluate", json={}, headers=headers)

        # =====================================================================
        # SCENARIO 3: Non-Compliant Imported Commodity (Rule 6(1)(f) Defect)
        # "Mediterranean Gold Olive Oil" (GTIN: 8905544332211)
        # =====================================================================
        print("\n--- [Scenario 3] Seeding Statutory Defect Demo (Missing Origin on Imported Item) ---")
        gtin3 = "8905544332211"
        p3 = client.post(
            "/api/v1/products",
            json={
                "brand_name": "Mediterranean Gold",
                "product_name": "Extra Virgin Olive Oil 500ml",
                "category": "Edible Oils",
                "commodity_type": "Imported Olive Oil",
                "gtin_barcode": gtin3,
                "manufacturer_claimed": "Global Fine Foods Importers, Mumbai",
            },
            headers=headers
        )
        product3_id = p3.json()["data"]["id"] if p3.status_code == 201 else client.get(f"/api/v1/products?gtin={gtin3}", headers=headers).json()["data"][0]["id"]
        print(f"[+] Product 3 registered: {product3_id}")

        ins3 = client.post(
            "/api/v1/inspections",
            json={
                "product_id": product3_id,
                "retail_outlet_name": "Le Marche Gourmet, Vasant Kunj",
                "retail_outlet_location": "Nelson Mandela Marg, New Delhi 110070",
                "notes": "Statutory inspection; imported container omits Country of Origin declaration",
            },
            headers=headers
        ).json()["data"]
        ins3_id = ins3["id"]
        print(f"  [+] Statutory Defect Inspection 3 created: {ins3_id}")

        img3 = create_synthetic_package_image("Mediterranean Gold Olive Oil", "Imported Commodity Missing Mandatory Rule 6(1)(f) Country of Origin")
        client.post(
            f"/api/v1/inspections/{ins3_id}/surfaces/FRONT_PDP/images",
            files={"file": ("olive_oil.jpg", img3, "image/jpeg")},
            headers=headers
        )

        obs_imported = [
            ("BRAND_NAME", "Mediterranean Gold", {"value": "Mediterranean Gold"}),
            ("PRODUCT_NAME", "Extra Virgin Olive Oil 500ml", {"value": "Extra Virgin Olive Oil 500ml"}),
            ("NET_QUANTITY", "500 ml", {"value": 500.0, "unit": "ml"}),
            ("MRP", "Rs. 690.00 (incl. of all taxes)", {"value": 690.0, "currency": "INR", "includes_taxes": True}),
            ("UNIT_SALE_PRICE", "Rs. 1.38 / ml", {"value": 1.38, "unit": "ml"}),
            ("DATE_OF_IMPORT", "01/2026", {"date_iso": "2026-01"}),
            ("IMPORTER_NAME", "Global Fine Foods Pvt Ltd, Ballard Estate, Mumbai 400001", {"name": "Global Fine Foods Pvt Ltd"}),
            ("CONSUMER_CARE_EMAIL", "care@globalfinefoods.in", {"emails": ["care@globalfinefoods.in"]}),
            # COUNTRY_OF_ORIGIN deliberately absent
        ]
        for ftype, raw, norm in obs_imported:
            client.post(
                "/api/v1/observations",
                json={
                    "inspection_id": ins3_id,
                    "field_type": ftype,
                    "raw_value": raw,
                    "normalized_value": norm,
                    "source": "OFFICER_INPUT",
                    "status": "VERIFIED",
                    "confidence": 0.96,
                },
                headers=headers
            )
        client.post(f"/api/v1/inspections/{ins3_id}/rules/evaluate", json={}, headers=headers)
        client.post(f"/api/v1/inspections/{ins3_id}/reports", json={"include_images": True}, headers=headers)

    print("\n" + "=" * 80)
    print(" [DEMO DATA SEEDING COMPLETE]")
    print("=" * 80)
    print("Key SIH 2026 Demonstration Entities Created:")
    print(" 1. Flagship Product: Himalayan Gold Organic Green Tea (GTIN: 8901234567890)")
    print(f"    - Baseline Inspection (v1.0): {ins1a_id}")
    print(f"    - Shrinkflation Revision (v2.0): {ins1b_id}")
    print(" 2. Live Adjudication Demo: Royal Basmati Reserve (GTIN: 8908765432109)")
    print(f"    - Dual Pricing Conflict: {ins2_id} (Status: IN_REVIEW / Needs Adjudication)")
    print(" 3. Statutory Defect Demo: Mediterranean Gold Olive Oil (GTIN: 8905544332211)")
    print(f"    - Defect (Rule 6(1)(f) Missing Origin): {ins3_id}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    seed_phase10_demo()
