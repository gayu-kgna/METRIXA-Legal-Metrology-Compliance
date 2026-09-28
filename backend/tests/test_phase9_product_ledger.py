import uuid
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from app.models.product import Product
from app.models.label_version import LabelVersion
from app.models.inspection import Inspection
from app.models.enums import InspectionOverallStatus
from app.services.product.ledger_service import (
    compute_label_fingerprint,
    compare_label_versions,
    resolve_or_create_label_version,
    build_product_timeline,
)

@pytest.mark.asyncio
async def test_deterministic_label_fingerprint():
    decls1 = {
        "MRP": "Rs. 250.00",
        "NET_QUANTITY": "500 g",
        "MANUFACTURER_NAME": "Metrixa Organics",
    }
    decls2 = {
        "NET_QUANTITY": "500 g",
        "MANUFACTURER_NAME": "Metrixa Organics",
        "MRP": "Rs. 250.00",
    }
    # Key order independent
    fp1 = compute_label_fingerprint(decls1)
    fp2 = compute_label_fingerprint(decls2)
    assert fp1 == fp2
    assert len(fp1) == 64

    # Value change creates new fingerprint
    decls3 = {**decls1, "MRP": "Rs. 270.00"}
    fp3 = compute_label_fingerprint(decls3)
    assert fp1 != fp3

@pytest.mark.asyncio
async def test_label_change_detection():
    v1 = LabelVersion(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        version_tag="v1.0",
        canonical_declarations={
            "MRP": "Rs. 100",
            "NET_QUANTITY": "1 kg",
            "MANUFACTURER_NAME": "Acme Foods",
            "BATCH_NUMBER": "B-001",
        },
    )
    v2 = LabelVersion(
        id=uuid.uuid4(),
        product_id=v1.product_id,
        version_tag="v2.0",
        canonical_declarations={
            "MRP": "Rs. 120", # Changed
            "NET_QUANTITY": "1 kg", # Unchanged
            "MANUFACTURER_NAME": "Acme Foods", # Unchanged
            "EXPIRY_DATE": "12/2026", # Added
            # BATCH_NUMBER removed
        },
    )
    diff = compare_label_versions(v1, v2)
    assert diff.from_version_tag == "v1.0"
    assert diff.to_version_tag == "v2.0"
    assert len(diff.changed_fields) == 1
    assert diff.changed_fields[0].field == "MRP"
    assert len(diff.added_fields) == 1
    assert diff.added_fields[0].field == "EXPIRY_DATE"
    assert len(diff.removed_fields) == 1
    assert diff.removed_fields[0].field == "BATCH_NUMBER"
    assert len(diff.unchanged_fields) == 2
    assert "deterministic rule engine" in diff.legal_disclaimer.lower()

@pytest.mark.asyncio
async def test_product_ledger_api(client: AsyncClient, auth_headers: dict, db_session):
    # Create test product
    unique_id = uuid.uuid4().hex[:8]
    unique_brand = f"TestBrand_{unique_id}"
    unique_gtin = f"test_{uuid.uuid4().hex[:12]}"
    p = Product(
        brand_name=unique_brand,
        product_name="Test Product 100g",
        category="Snacks",
        gtin_barcode=unique_gtin,
        manufacturer_claimed="Test Maker Pvt Ltd",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    # 1. Query ledger
    resp = await client.get(f"/api/v1/products?q={unique_brand}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(x["id"] == str(p.id) for x in data)

    # 2. Get product detail
    detail_resp = await client.get(f"/api/v1/products/{p.id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    p_data = detail_resp.json()["data"]
    assert p_data["brand_name"] == unique_brand
    assert p_data["inspection_count"] == 0

    # 3. Add inspection for this product
    insp_resp = await client.post(
        "/api/v1/inspections",
        json={
            "product_id": str(p.id),
            "retail_outlet_name": "Test Outlet",
            "retail_outlet_address": "Test Address",
        },
        headers=auth_headers,
    )
    assert insp_resp.status_code == 201
    insp_id = insp_resp.json()["data"]["id"]

    # 4. Check inspections history endpoint
    insps_resp = await client.get(f"/api/v1/products/{p.id}/inspections", headers=auth_headers)
    assert insps_resp.status_code == 200
    insps_data = insps_resp.json()["data"]
    assert len(insps_data) == 1
    assert insps_data[0]["id"] == insp_id

    # 5. Timeline endpoint
    timeline_resp = await client.get(f"/api/v1/products/{p.id}/timeline", headers=auth_headers)
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()["data"]
    assert len(events) >= 2
    types = [e["event_type"] for e in events]
    assert "PRODUCT_REGISTERED" in types
    assert "INSPECTION_CREATED" in types

@pytest.mark.asyncio
async def test_analytics_api_endpoints(client: AsyncClient, auth_headers: dict):
    # Overview
    overview_resp = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert overview_resp.status_code == 200
    ov = overview_resp.json()["data"]
    assert "total_inspections" in ov
    assert "products_inspected" in ov

    # Inspections Trend
    trend_resp = await client.get("/api/v1/analytics/inspections?days=14", headers=auth_headers)
    assert trend_resp.status_code == 200
    assert isinstance(trend_resp.json()["data"], list)

    # Outcomes
    outcomes_resp = await client.get("/api/v1/analytics/outcomes", headers=auth_headers)
    assert outcomes_resp.status_code == 200
    oc = outcomes_resp.json()["data"]
    assert "pass_count" in oc

    # Categories
    cats_resp = await client.get("/api/v1/analytics/categories", headers=auth_headers)
    assert cats_resp.status_code == 200
    assert isinstance(cats_resp.json()["data"], list)

    # Locations
    locs_resp = await client.get("/api/v1/analytics/locations", headers=auth_headers)
    assert locs_resp.status_code == 200
    assert isinstance(locs_resp.json()["data"], list)

    # Adjudications
    adjs_resp = await client.get("/api/v1/analytics/adjudications", headers=auth_headers)
    assert adjs_resp.status_code == 200
    assert isinstance(adjs_resp.json()["data"], list)

@pytest.mark.asyncio
async def test_unauthorized_product_ledger_access(client: AsyncClient):
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 401
    
    analytics_resp = await client.get("/api/v1/analytics/overview")
    assert analytics_resp.status_code == 401
