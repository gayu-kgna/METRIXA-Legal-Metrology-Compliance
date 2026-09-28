import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_product_lifecycle_and_separation(client: AsyncClient, inspector_token: str):
    """
    Test product creation, barcode uniqueness, and separation from inspections.
    A product can have multiple inspections and label versions over time.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}
    gtin = f"890{uuid.uuid4().hex[:10]}"

    # 1. Create Product
    prod_payload = {
        "gtin_barcode": gtin,
        "brand_name": "Haldiram's",
        "product_name": "Bhujia Sev 400g",
        "category": "Snacks & Savouries",
        "commodity_type": "Packaged Food",
        "manufacturer_claimed": "Haldiram Snacks Pvt. Ltd., Noida, UP",
        "metadata_json": {"target_weight_g": 400}
    }
    resp = await client.post("/api/v1/products", json=prod_payload, headers=headers)
    assert resp.status_code == 201
    product = resp.json()["data"]
    prod_id = product["id"]

    # 2. Prevent duplicate GTIN
    dup_resp = await client.post("/api/v1/products", json=prod_payload, headers=headers)
    assert dup_resp.status_code == 400

    # 3. Create Label Version
    label_payload = {
        "version_tag": "v1.0-2026",
        "canonical_declarations": {
            "mrp": "MRP Rs 110.00 (incl. of all taxes)",
            "net_weight": "400 g",
            "fssai_lic": "10012011000123"
        },
        "notes": "Standard festival packaging artwork"
    }
    label_resp = await client.post(f"/api/v1/products/{prod_id}/label-versions", json=label_payload, headers=headers)
    assert label_resp.status_code == 201

    # 4. Associate two separate inspections with the same product
    ins1_resp = await client.post("/api/v1/inspections", json={
        "product_id": prod_id,
        "retail_outlet_name": "Blinkit Dark Store Saket",
        "notes": "Inspection 1 at retail dark store"
    }, headers=headers)
    assert ins1_resp.status_code == 201

    ins2_resp = await client.post("/api/v1/inspections", json={
        "product_id": prod_id,
        "retail_outlet_name": "Big Bazaar Vasant Kunj",
        "notes": "Inspection 2 at hypermarket"
    }, headers=headers)
    assert ins2_resp.status_code == 201

    # 5. Verify product timeline aggregates both inspections without overwriting
    timeline_resp = await client.get(f"/api/v1/products/{prod_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()["data"]
    assert isinstance(timeline, list)
    insp_events = [e for e in timeline if e["event_type"] == "INSPECTION_CREATED"]
    assert len(insp_events) == 2
    label_events = [e for e in timeline if e["event_type"] == "LABEL_VERSION_OBSERVED"]
    assert len(label_events) >= 1

    # Product detail reflects aggregated inspections and brand
    prod_detail_resp = await client.get(f"/api/v1/products/{prod_id}", headers=headers)
    assert prod_detail_resp.status_code == 200
    prod_detail = prod_detail_resp.json()["data"]
    assert prod_detail["inspection_count"] == 2
    assert prod_detail["brand_name"] == "Haldiram's"

