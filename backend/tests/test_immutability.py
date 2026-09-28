import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_historical_records_cannot_be_silently_overwritten(
    client: AsyncClient,
    inspector_token: str,
    adjudicator_token: str,
):
    """
    CRITICAL ARCHITECTURAL SAFEGUARD TEST:
    Verify that historical observations CANNOT be silently overwritten.
    Every update creates a new versioned revision, preserves the prior ground truth,
    links the superseded record, and writes to the tamper-evident audit log.
    """
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # 1. Initialize an inspection
    ins_resp = await client.post("/api/v1/inspections", json={
        "retail_outlet_name": "Kirana Store Lajpat Nagar",
        "notes": "Testing immutability safeguards"
    }, headers=headers)
    ins_id = ins_resp.json()["data"]["id"]

    # 2. Record Initial Perception Observation (Revision 1)
    initial_payload = {
        "inspection_id": ins_id,
        "field_type": "NET_QUANTITY_VALUE",
        "raw_value": "Net Qty: 45O g",  # Note OCR error 'O' instead of '0'
        "normalized_value": {"quantity": 450, "unit": "g", "ocr_raw": "45O"},
        "source": "CAMERA_STREAM",
        "confidence": 0.81,
        "status": "OBSERVED",
        "bounding_box": {"ymin": 0.50, "xmin": 0.20, "ymax": 0.55, "xmax": 0.40}
    }
    obs_resp = await client.post("/api/v1/observations", json=initial_payload, headers=headers)
    assert obs_resp.status_code == 201
    rev1 = obs_resp.json()["data"]
    rev1_id = rev1["id"]
    assert rev1["revision"] == 1
    assert rev1["is_latest"] is True
    assert rev1["status"] == "OBSERVED"
    assert rev1["superseded_by_id"] is None

    # 3. Adjudicate / Revise the Observation (Creates Revision 2)
    revision_payload = {
        "raw_value": "Net Qty: 450 g",  # Corrected to digit 0
        "normalized_value": {"quantity": 450, "unit": "g", "ocr_corrected": True},
        "status": "VERIFIED",
        "revision_reason": "Corrected OCR token 'O' to digit '0' based on visual inspection of original package image."
    }
    revise_resp = await client.post(
        f"/api/v1/observations/{rev1_id}/revise",
        json=revision_payload,
        headers=headers
    )
    assert revise_resp.status_code == 201
    rev2 = revise_resp.json()["data"]
    rev2_id = rev2["id"]
    assert rev2["revision"] == 2
    assert rev2["is_latest"] is True
    assert rev2["status"] == "VERIFIED"
    assert rev2["raw_value"] == "Net Qty: 450 g"
    assert rev2["revision_reason"] == revision_payload["revision_reason"]

    # 4. Verify Revision 1 was PRESERVED and NOT overwritten!
    # By default, list endpoint returns only is_latest=True
    active_obs_resp = await client.get(f"/api/v1/observations/inspection/{ins_id}", headers=headers)
    active_obs = active_obs_resp.json()["data"]
    assert len(active_obs) == 1
    assert active_obs[0]["id"] == rev2_id
    assert active_obs[0]["revision"] == 2

    # When querying with include_history=True, both revisions exist!
    history_obs_resp = await client.get(
        f"/api/v1/observations/inspection/{ins_id}?include_history=true",
        headers=headers
    )
    all_revisions = history_obs_resp.json()["data"]
    assert len(all_revisions) == 2
    
    rev1_in_db = next(r for r in all_revisions if r["id"] == rev1_id)
    assert rev1_in_db["is_latest"] is False
    assert rev1_in_db["superseded_by_id"] == rev2_id
    assert rev1_in_db["raw_value"] == "Net Qty: 45O g"  # Original raw OCR preserved unchanged!

    # 5. Prevent revising an already superseded revision
    fail_revise_resp = await client.post(
        f"/api/v1/observations/{rev1_id}/revise",
        json={"raw_value": "Invalid", "revision_reason": "Attempting to branch from stale revision"},
        headers=headers
    )
    assert fail_revise_resp.status_code == 400

    # 6. Verify audit log entry was created for the revision (accessed via adjudicator role)
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}
    audit_resp = await client.get(f"/api/v1/audit?inspection_id={ins_id}", headers=adj_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]
    assert len(logs) >= 1
    audit_entry = next(l for l in logs if l["action"] == "OBSERVATION_REVISED")
    assert audit_entry["previous_state"]["raw_value"] == "Net Qty: 45O g"
    assert audit_entry["new_state"]["raw_value"] == "Net Qty: 450 g"
    assert audit_entry["justification"] == revision_payload["revision_reason"]
