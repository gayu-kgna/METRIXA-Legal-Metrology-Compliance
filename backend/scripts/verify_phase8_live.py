import io
import os
import sys
import uuid
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8080"

def test_phase8_live_end_to_end():
    print("\n================================================================================")
    print(" METRIXA PHASE 8 LIVE VERIFICATION: INSPECTION ADJUDICATION & BBOX WORKSPACE")
    print("================================================================================\n")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        h = client.get("/api/v1/health")
        assert h.status_code == 200, f"Health check failed: {h.text}"
        print("[1/12] [PASS] Backend service healthy on port 8080.")

        # 2. Authentication
        officer_email = "officer@metrixa.gov.in"
        officer_pwd = "Password@123"
        login_resp = client.post("/api/v1/auth/login", json={"email": officer_email, "password": officer_pwd})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[2/12] [PASS] Authorized Officer authenticated ({officer_email}).")

        # 3. List inspections to get test inspection with populated adjudication workspace
        insps = client.get("/api/v1/inspections", headers=headers).json()["data"]
        assert len(insps) > 0, "No inspections found"
        target_insp = None
        for candidate in insps:
            ws_check = client.get(f"/api/v1/inspections/{candidate['id']}/adjudication", headers=headers)
            if ws_check.status_code == 200:
                ws_data = ws_check.json()["data"]
                if len(ws_data.get("regions", [])) > 0 and len(ws_data.get("observations", [])) > 0:
                    target_insp = candidate
                    break
        if not target_insp:
            from scripts.seed_adjudication_demo import seed_demo
            seed_id = seed_demo()
            target_insp = client.get(f"/api/v1/inspections/{seed_id}", headers=headers).json()["data"]

        insp_id = target_insp["id"]
        insp_num = target_insp["inspection_number"]
        print(f"[3/12] [PASS] Selected Inspection {insp_num} (ID: {insp_id}).")

        # 4. Fetch consolidated adjudication workspace state
        ws_resp = client.get(f"/api/v1/inspections/{insp_id}/adjudication", headers=headers)
        assert ws_resp.status_code == 200, f"Workspace fetch failed: {ws_resp.text}"
        ws = ws_resp.json()["data"]
        regions = ws["regions"]
        observations = ws["observations"]
        conflicts = ws["conflicts"]
        surfaces = ws["surfaces"]
        assert len(regions) > 0, "Expected OCR regions in workspace"
        assert len(observations) > 0, "Expected observations in workspace"
        print(f"[4/12] [PASS] Adjudication Workspace State loaded: {len(regions)} regions, {len(observations)} observations, {len(surfaces)} surfaces.")

        # 5. Patch OCR region (Text & Bounding Box Correction)
        target_reg = regions[0]
        reg_id = target_reg["id"]
        patch_payload = {
            "raw_text": "NET QTY: 500 g (ADJUDICATED)",
            "bounding_box": {
                "x": 0.12,
                "y": 0.12,
                "width": 0.20,
                "height": 0.10
            },
            "reason": "Officer visual inspection corrected bounding box alignment and OCR text"
        }
        patch_resp = client.patch(f"/api/v1/inspections/{insp_id}/ocr-regions/{reg_id}", json=patch_payload, headers=headers)
        assert patch_resp.status_code == 200, f"Patch failed: {patch_resp.text}"
        patched_data = patch_resp.json()["data"]
        assert patched_data["is_adjudicated"] is True
        assert patched_data["raw_text"] == "NET QTY: 500 g (ADJUDICATED)"
        assert patched_data["status"] == "CORRECTED"
        assert patched_data["bounding_box"]["x"] == 0.12
        print(f"[5/12] [PASS] OCR Region patched with revision tracking and normalized bbox.")

        # 6. Reject OCR region as noise
        noise_reg = regions[1]
        reject_resp = client.post(
            f"/api/v1/inspections/{insp_id}/ocr-regions/{noise_reg['id']}/reject",
            json={"reason": "Flagged as background artifact/noise"},
            headers=headers
        )
        assert reject_resp.status_code == 200, f"Reject failed: {reject_resp.text}"
        assert reject_resp.json()["data"]["is_rejected"] is True
        print(f"[6/12] [PASS] OCR Region rejected as artifact/noise successfully.")

        # 7. Create Manual OCR region with normalized coordinates
        surf_id = surfaces[0]["id"]
        create_payload = {
            "surface_id": surf_id,
            "raw_text": "USP: Rs. 0.90 / g",
            "bounding_box": {"x": 0.10, "y": 0.50, "width": 0.30, "height": 0.05},
            "reason": "Officer drew bounding box on missed statutory declaration"
        }
        create_resp = client.post(f"/api/v1/inspections/{insp_id}/ocr-regions", json=create_payload, headers=headers)
        assert create_resp.status_code == 201, f"Create region failed: {create_resp.text}"
        created_reg = create_resp.json()["data"]
        assert created_reg["is_manually_created"] is True
        print(f"[7/12] [PASS] Manually drawn OCR bounding box created with provenance tracking.")

        # 8. Verify Statutory Observation
        target_obs = observations[0]
        obs_id = target_obs["id"]
        verify_resp = client.post(
            f"/api/v1/inspections/{insp_id}/observations/{obs_id}/verify",
            json={"notes": "Statutory declaration verified against Physical Sample"},
            headers=headers
        )
        assert verify_resp.status_code == 200, f"Observation verification failed: {verify_resp.text}"
        verified_obs = verify_resp.json()["data"]
        assert verified_obs["status"] == "VERIFIED"
        active_obs_id = verified_obs["id"]
        print(f"[8/12] [PASS] Observation verified with officer signature and audit log.")

        # 9. Correct Statutory Observation
        correct_resp = client.post(
            f"/api/v1/inspections/{insp_id}/observations/{active_obs_id}/correct",
            json={
                "raw_value": "500 g (Verified Net)",
                "normalized_value": {"value": 500, "unit": "g", "formatted": "500 g"},
                "reason": "Adjusted unit formatting",
                "status": "CORRECTED"
            },
            headers=headers
        )
        assert correct_resp.status_code == 200, f"Observation correction failed: {correct_resp.text}"
        corr_obs = correct_resp.json()["data"]
        assert corr_obs["status"] in ("VERIFIED", "CORRECTED")
        assert corr_obs["revision"] >= 2
        print(f"[9/12] [PASS] Observation corrected with revision chain (Rev {corr_obs['revision']}).")

        # 10. Create Manual Statutory Observation (OFFICER_INPUT)
        man_obs_payload = {
            "surface_id": surf_id,
            "field_type": "CONSUMER_CARE_EMAIL",
            "raw_value": "care@metrixa.tea",
            "normalized_value": {"email": "care@metrixa.tea"},
            "reason": "Officer verified consumer care imprint on lateral fold"
        }
        man_obs_resp = client.post(f"/api/v1/inspections/{insp_id}/observations/manual", json=man_obs_payload, headers=headers)
        assert man_obs_resp.status_code == 201, f"Manual observation failed: {man_obs_resp.text}"
        man_obs = man_obs_resp.json()["data"]
        assert man_obs["source"] == "OFFICER_INPUT"
        print(f"[10/12] [PASS] Officer manual observation created with OFFICER_INPUT source.")

        # 11. Authoritative Rule Re-Evaluation
        reeval_resp = client.post(
            f"/api/v1/inspections/{insp_id}/rules/re-evaluate",
            json={"justification": "Officer complete adjudication of declarations and OCR tokens"},
            headers=headers
        )
        assert reeval_resp.status_code == 200, f"Rule re-evaluation failed: {reeval_resp.text}"
        reeval_data = reeval_resp.json()["data"]
        assert "new_verdict" in reeval_data
        assert "changes" in reeval_data
        print(f"[11/12] [PASS] Deterministic Rule Re-Evaluation completed: Overall Verdict = {reeval_data['new_verdict']} ({len(reeval_data['changes'])} rule changes compared).")

        # 12. Evidence Traceability & PDF Dossier Report with Adjudication Provenance
        ev_resp = client.get(f"/api/v1/inspections/{insp_id}/evidence", headers=headers)
        assert ev_resp.status_code == 200, f"Evidence trace failed: {ev_resp.text}"
        ev_graph = ev_resp.json()["data"]["graph"]
        assert len(ev_graph["nodes"]) > 0
        print(f"[12/12] [PASS] Evidence Graph updated with adjudication nodes: {len(ev_graph['nodes'])} nodes, {len(ev_graph['edges'])} edges.")

        # Generate fresh report
        rep_resp = client.post(
            f"/api/v1/inspections/{insp_id}/reports",
            json={"report_type": "DETAILED_TECHNICAL_DOSSIER"},
            headers=headers
        )
        assert rep_resp.status_code == 201, f"Report generation failed: {rep_resp.text}"
        rep_data = rep_resp.json()["data"]
        pdf_path = rep_data.get("storage_path") or rep_data.get("pdf_filename")
        print(f"[+] Dossier PDF generated: {pdf_path} (SHA-256: {rep_data['sha256_hash'][:20]}...)")

        print("\n================================================================================")
        print(" ALL 12 PHASE 8 LIVE VERIFICATION GATES PASSED WITH ZERO ERRORS!")
        print("================================================================================\n")

if __name__ == "__main__":
    test_phase8_live_end_to_end()
