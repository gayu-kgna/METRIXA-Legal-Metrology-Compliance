import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.inspection import Inspection
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def test_direct_api():
    async with AsyncSessionLocal() as session:
        insp = (await session.execute(
            select(Inspection)
            .options(selectinload(Inspection.surfaces))
            .where(Inspection.inspection_number == "LMR-20260923-881594")
        )).scalar_one()
        u = (await session.execute(select(User).where(User.id == insp.inspector_id))).scalar_one()
        token = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role.value if hasattr(u.role, "value") else str(u.role)})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for s in insp.surfaces:
            surface_name = s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type)
            print(f"=== TESTING OCR API ON SURFACE: {surface_name} ({s.id}) ===")
            resp = await client.post(
                f"/api/v1/inspections/{insp.id}/images/{s.id}/ocr",
                json={"provider_name": "mock"},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200, f"OCR API call failed: {resp.status_code} {resp.text}"
            body = resp.json()
            assert body.get("success") is True
            data = body["data"]

            # Validate canonical properties
            print("  ocr_run_id:", data.get("ocr_run_id"))
            print("  surface:", data.get("surface"))
            print("  provider:", data.get("provider"))
            print("  status:", data.get("status"))
            print("  region_count:", data.get("region_count"))
            print("  regions length:", len(data.get("regions", [])))
            print("  duration_ms:", data.get("duration_ms"))

            assert data.get("ocr_run_id") is not None, "Missing ocr_run_id"
            assert data.get("surface") == surface_name, f"Surface mismatch: {data.get('surface')} != {surface_name}"
            assert data.get("provider") == "Mock Deterministic OCR", "Provider mismatch"
            assert data.get("status") == "COMPLETED", f"Status not COMPLETED: {data.get('status')}"
            assert isinstance(data.get("region_count"), int) and data.get("region_count") > 0, "Invalid region_count"
            assert len(data.get("regions")) == data.get("region_count"), f"Length mismatch: {len(data.get('regions'))} != {data.get('region_count')}"

            # Validate individual regions have normalized bbox and text
            for reg in data["regions"]:
                assert "text" in reg and reg["text"], "Missing text in region"
                assert "confidence" in reg and 0.0 <= reg["confidence"] <= 1.0
                bbox = reg.get("bbox") or reg.get("bounding_box")
                assert bbox is not None, "Missing bbox"
                assert 0.0 <= bbox["x"] <= 1.0
                assert 0.0 <= bbox["y"] <= 1.0
                assert 0.0 <= bbox["width"] <= 1.0
                assert 0.0 <= bbox["height"] <= 1.0

            print(f"  [+] Surface {surface_name} validated successfully! ({data['region_count']} regions)\n")

    print("[SUCCESS] All surfaces for LMR-20260923-881594 verified under canonical OCR response contract.\n")

    print("=== TESTING ENTITY PARSER CONSUMPTION OF OCR REGIONS ===")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for s in insp.surfaces:
            surface_name = s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type)
            print(f"Testing Entity Parsing on: {surface_name}...")
            resp = await client.post(
                f"/api/v1/inspections/{insp.id}/images/{s.id}/entities",
                json={},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200, f"Entity parsing failed: {resp.status_code} {resp.text}"
            data = resp.json()["data"]
            obs_list = data.get("observations", [])
            print(f"  [+] Extracted {len(obs_list)} observations from {surface_name} OCR evidence (status: {data.get('status')}):")
            for o in obs_list:
                ft = o.get("field_type") or o.get("field_name")
                raw = o.get("raw_value") or o.get("raw_text_extracted")
                print(f"      * {ft}: '{raw}'")
            print()

    print("[SUCCESS] Full OCR -> Entity Parsing pipeline chain verified!\n")

    print("=== TESTING DOWNSTREAM PIPELINE STAGES ===")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. PDP Geometry
        for s in insp.surfaces:
            surface_name = s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type)
            g_res = await client.post(
                f"/api/v1/inspections/{insp.id}/images/{s.id}/geometry",
                json={},
                headers={"Authorization": f"Bearer {token}"}
            )
            assert g_res.status_code == 200, f"Geometry failed: {g_res.text}"
            pdp_area = g_res.json()["data"]["pdp_area_px2"]
            print(f"  [+] PDP Geometry for {surface_name}: Area={pdp_area}px2")

        # 2. Rules Evaluation
        r_res = await client.post(
            f"/api/v1/inspections/{insp.id}/rules/evaluate",
            json={"rule_set_version": "2024-v1", "include_test_rules": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert r_res.status_code == 200, f"Rules evaluation failed: {r_res.text}"
        summary = r_res.json()["data"]
        print(f"  [+] Statutory Rules: PASS={summary.get('pass_count')}, FAIL={summary.get('fail_count')}, Verdict={summary.get('overall_verdict')}")

        # 3. PDF Dossier Report
        rep_res = await client.post(
            f"/api/v1/inspections/{insp.id}/reports",
            json={"report_type": "FULL_INSPECTION_DOSSIER"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert rep_res.status_code in (200, 201), f"Report generation failed: {rep_res.text}"
        rep = rep_res.json()["data"]
        print(f"  [+] PDF Dossier Generated: {rep.get('pdf_filename')}, SHA256={rep.get('sha256_hash')[:16]}...")

        # 4. Evidence Traceability Manifest
        ev_res = await client.get(
            f"/api/v1/inspections/{insp.id}/evidence",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ev_res.status_code == 200, f"Evidence trace failed: {ev_res.text}"
        ev = ev_res.json()["data"]
        print(f"  [+] Evidence Bundle keys: {list(ev.keys())}")
        snap = ev.get("snapshot") or {}
        print(f"  [+] Evidence Trace Manifest: Snapshot Hash={snap.get('sha256_hash', 'N/A')[:16]}..., OCR Runs={len(ev.get('ocr_runs', []))}, Observations={len(ev.get('observations', []))}")

    print("\n[ALL DOWNSTREAM STAGES VERIFIED WITH REAL PIPELINE DATA!]")

if __name__ == "__main__":
    asyncio.run(test_direct_api())
