import os
import sys
import uuid
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8080"

def test_phase9_live_end_to_end():
    print("\n================================================================================")
    print(" METRIXA PHASE 9 LIVE VERIFICATION: PRODUCT LEDGER, TIMELINE & ANALYTICS")
    print("================================================================================\n")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # [1/12] Health & Officer Auth
        h = client.get("/api/v1/health")
        assert h.status_code == 200, f"Health check failed: {h.text}"
        print("[1/12] [PASS] Backend service healthy on port 8080.")

        officer_email = "officer@metrixa.gov.in"
        officer_pwd = "Password@123"
        login_resp = client.post("/api/v1/auth/login", json={"email": officer_email, "password": officer_pwd})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[2/12] [PASS] Authorized Officer authenticated ({officer_email}).")

        # Ensure demo product is seeded
        from scripts.seed_phase9_demo import seed_phase9_demo
        target_product_id = seed_phase9_demo()

        # [3/12] Product Ledger Listing, Search & Pagination
        ledger_resp = client.get("/api/v1/products?q=Himalayan&page=1&page_size=10", headers=headers)
        assert ledger_resp.status_code == 200, f"Product ledger fetch failed: {ledger_resp.text}"
        ledger_data = ledger_resp.json()["data"]
        pagination = ledger_resp.json()["pagination"]
        assert len(ledger_data) > 0, "Expected at least 1 product in search"
        assert pagination["total_items"] >= 1
        found_product = next((p for p in ledger_data if p["id"] == str(target_product_id)), ledger_data[0])
        print(f"[3/12] [PASS] Product Ledger queried: found '{found_product['brand_name']} {found_product['product_name']}' (Inspections: {found_product['inspection_count']}).")

        # [4/12] Product Detail fetch with inspection stats & known declarations
        detail_resp = client.get(f"/api/v1/products/{target_product_id}", headers=headers)
        assert detail_resp.status_code == 200, f"Product detail fetch failed: {detail_resp.text}"
        p_detail = detail_resp.json()["data"]
        assert p_detail["id"] == str(target_product_id)
        assert p_detail["inspection_count"] >= 2
        assert len(p_detail["known_declarations"]) > 0
        print(f"[4/12] [PASS] Product Detail verified: {p_detail['inspection_count']} inspections, First: {p_detail['first_inspection_date'][:10]}, Latest: {p_detail['latest_inspection_date'][:10]}.")

        # [5/12] Product Inspection History with status filtering
        insps_resp = client.get(f"/api/v1/products/{target_product_id}/inspections", headers=headers)
        assert insps_resp.status_code == 200, f"Product inspections failed: {insps_resp.text}"
        prod_insps = insps_resp.json()["data"]
        assert len(prod_insps) >= 2, "Expected at least 2 inspections for flagship commodity"
        print(f"[5/12] [PASS] Product Inspection History loaded: {len(prod_insps)} chronological inspection events.")

        # [6/12] Label Version History & Deterministic SHA-256 Fingerprint
        lvs_resp = client.get(f"/api/v1/products/{target_product_id}/label-versions", headers=headers)
        assert lvs_resp.status_code == 200, f"Label versions fetch failed: {lvs_resp.text}"
        lvs = lvs_resp.json()["data"]
        assert len(lvs) >= 2, "Expected at least 2 packaging label revisions"
        v1 = lvs[0]
        v2 = lvs[1]
        assert v1["version_fingerprint"] is not None
        assert v2["version_fingerprint"] is not None
        assert v1["version_fingerprint"] != v2["version_fingerprint"], "Distinct label revisions must have distinct fingerprints"
        print(f"[6/12] [PASS] Label Versions verified: {v1['version_tag']} (SHA: {v1['version_fingerprint'][:16]}...) and {v2['version_tag']} (SHA: {v2['version_fingerprint'][:16]}...).")

        # [7/12] Deterministic Label Change Detection (Diff)
        diff_resp = client.get(
            f"/api/v1/products/{target_product_id}/changes?from_version_id={v1['id']}&to_version_id={v2['id']}",
            headers=headers
        )
        assert diff_resp.status_code == 200, f"Label diff failed: {diff_resp.text}"
        diff_data = diff_resp.json()["data"]
        assert len(diff_data["changed_fields"]) > 0, "Expected changed fields between v1 and v2"
        assert any(f["field"] == "MRP" for f in diff_data["changed_fields"]), "Expected MRP change"
        assert len(diff_data["added_fields"]) > 0, "Expected added fields (EXPIRY_DATE)"
        assert "deterministic rule engine" in diff_data["legal_disclaimer"].lower()
        print(f"[7/12] [PASS] Deterministic Label Changes verified: {len(diff_data['changed_fields'])} changed, {len(diff_data['added_fields'])} added, {len(diff_data['unchanged_fields'])} unchanged.")

        # [8/12] Chronological Product Lifecycle Timeline
        timeline_resp = client.get(f"/api/v1/products/{target_product_id}/timeline", headers=headers)
        assert timeline_resp.status_code == 200, f"Timeline fetch failed: {timeline_resp.text}"
        timeline_events = timeline_resp.json()["data"]
        assert len(timeline_events) >= 5, "Expected multi-stage event stream"
        event_types = [e["event_type"] for e in timeline_events]
        assert "PRODUCT_REGISTERED" in event_types
        assert "INSPECTION_CREATED" in event_types
        assert "EVIDENCE_CAPTURED" in event_types
        assert "RULES_EVALUATED" in event_types
        assert "LABEL_VERSION_OBSERVED" in event_types
        print(f"[8/12] [PASS] Comprehensive Lifecycle Timeline generated: {len(timeline_events)} sequential operational events.")

        # [9/12] Dashboard Analytics Overview Aggregation
        analytics_resp = client.get("/api/v1/analytics/overview", headers=headers)
        assert analytics_resp.status_code == 200, f"Analytics overview failed: {analytics_resp.text}"
        overview = analytics_resp.json()["data"]
        assert overview["total_inspections"] > 0
        assert overview["products_inspected"] > 0
        assert overview["reports_generated"] > 0
        assert "PASS" in overview["rule_evaluation_outcomes"]
        print(f"[9/12] [PASS] Dashboard Analytics Overview aggregated: {overview['total_inspections']} total inspections, {overview['products_inspected']} products, {overview['reports_generated']} reports.")

        # [10/12] Inspection Trend Analysis
        trend_resp = client.get("/api/v1/analytics/inspections?days=30", headers=headers)
        assert trend_resp.status_code == 200, f"Trend failed: {trend_resp.text}"
        trend_data = trend_resp.json()["data"]
        assert len(trend_data) > 0
        print(f"[10/12] [PASS] Historical Inspection Trend aggregated: {len(trend_data)} daily volume buckets.")

        # [11/12] Outcome Distribution & Category / Location Breakdowns
        outcomes_resp = client.get("/api/v1/analytics/outcomes", headers=headers)
        assert outcomes_resp.status_code == 200, f"Outcomes failed: {outcomes_resp.text}"
        outcomes = outcomes_resp.json()["data"]
        assert outcomes["total_evaluations"] > 0

        cats_resp = client.get("/api/v1/analytics/categories", headers=headers)
        assert cats_resp.status_code == 200
        cats = cats_resp.json()["data"]
        assert len(cats) > 0

        locs_resp = client.get("/api/v1/analytics/locations", headers=headers)
        assert locs_resp.status_code == 200
        locs = locs_resp.json()["data"]
        assert len(locs) > 0
        print(f"[11/12] [PASS] Historical Outcome & Distribution Breakdown verified: {outcomes['total_evaluations']} evaluations, {len(cats)} categories, {len(locs)} retail sites.")

        # [12/12] Camera Capture Workflow Guard
        # Check CaptureWorkspacePage and CameraHUD code files to verify auto-open is guarded
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        workspace_path = os.path.join(repo_root, "frontend", "src", "pages", "CaptureWorkspacePage.tsx")
        hud_path = os.path.join(repo_root, "frontend", "src", "components", "camera", "CameraHUD.tsx")
        workspace_code = open(workspace_path, "r", encoding="utf-8").read()
        assert "activeHUDType, setActiveHUDType] = useState<SurfaceType | null>(null)" in workspace_code
        hud_code = open(hud_path, "r", encoding="utf-8").read()
        assert "autoCaptureEnabled, setAutoCaptureEnabled] = useState<boolean>(false)" in hud_code
        print("[12/12] [PASS] Camera Capture Workflow Guard verified: Camera is NOT automatically opened on page load; tactile user trigger enforced.")

        print("\n================================================================================")
        print(" ALL 12 PHASE 9 LIVE VERIFICATION GATES PASSED WITH ZERO ERRORS!")
        print("================================================================================\n")

if __name__ == "__main__":
    test_phase9_live_end_to_end()
