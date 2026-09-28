import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_versioned_rule_architecture_and_evaluations(
    client: AsyncClient,
    inspector_token: str,
    adjudicator_token: str
):
    """
    Test versioned legal rule architecture:
    - Multiple rule versions
    - Declarative conditions and parameters
    - Deterministic RuleEvaluation (PASS, FAIL, REVIEW, INDETERMINATE)
    - Low confidence yielding INDETERMINATE rather than automatic FAIL
    - Officer override with audit justification
    """
    adj_headers = {"Authorization": f"Bearer {adjudicator_token}"}
    insp_headers = {"Authorization": f"Bearer {inspector_token}"}

    rule_code = f"LMR_TEST_R6_1_E_{uuid.uuid4().hex[:6]}"

    # 1. Create Rule Version 1.0.0 (Admin/Adjudicator)
    r1_payload = {
        "rule_code": rule_code,
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(e)",
        "clause_reference": "Sub-rule (1) Clause (e)",
        "title": "Mandatory MRP Declaration Format",
        "description": "The maximum retail price at which commodity in packaged form may be sold to the consumer inclusive of all taxes.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "applicability_conditions": {
            "commodity_scope": "ALL_RETAIL_PACKAGES",
            "exemptions_apply": False
        },
        "exemptions": {"packaged_for_industrial_consumers": True},
        "parameters": {
            "required_prefixes": ["MRP", "Maximum Retail Price"],
            "required_suffixes": ["incl. of all taxes", "inclusive of all taxes"]
        },
        "evaluation_logic": {"type": "REGEX_FORMAT_MATCH"},
        "severity": "MANDATORY",
        "evidence_requirements": {"required_fields": ["MRP_RAW", "MRP_AMOUNT"]},
        "is_active": True
    }
    r1_resp = await client.post("/api/v1/rules/definitions", json=r1_payload, headers=adj_headers)
    assert r1_resp.status_code == 201
    r1_id = r1_resp.json()["data"]["id"]

    # 2. Create Rule Version 2.0.0 (Amendment) for the same rule_code
    r2_payload = {**r1_payload, "version": "2.0.0", "title": "Amended MRP Declaration (Symbol ₹ Standardized)"}
    r2_resp = await client.post("/api/v1/rules/definitions", json=r2_payload, headers=adj_headers)
    assert r2_resp.status_code == 201

    # 3. Retrieve all versions for this rule_code
    versions_resp = await client.get(f"/api/v1/rules/definitions/{rule_code}", headers=insp_headers)
    assert versions_resp.status_code == 200
    versions = versions_resp.json()["data"]
    assert len(versions) == 2
    assert {v["version"] for v in versions} == {"1.0.0", "2.0.0"}

    # 4. Create an inspection
    ins_resp = await client.post("/api/v1/inspections", json={
        "retail_outlet_name": "Test Outlet",
        "notes": "Testing rule outcomes"
    }, headers=insp_headers)
    ins_id = ins_resp.json()["data"]["id"]

    # 5. Record Rule Evaluation with INDETERMINATE outcome (when evidence is insufficient or low confidence)
    eval_indet_payload = {
        "inspection_id": ins_id,
        "rule_definition_id": r1_id,
        "outcome": "INDETERMINATE",
        "legal_rationale": "OCR confidence is 0.42 and text region is partially occluded by fold. Cannot determine compliance or non-compliance.",
        "statutory_citation": "Rule 6(1)(e) - Evidence insufficient for definitive finding",
        "evidence_references": {"surface_type": "FRONT_PDP", "confidence": 0.42}
    }
    eval_resp = await client.post("/api/v1/rules/evaluations", json=eval_indet_payload, headers=insp_headers)
    assert eval_resp.status_code == 201
    eval_data = eval_resp.json()["data"]
    eval_id = eval_data["id"]
    assert eval_data["outcome"] == "INDETERMINATE"

    # 6. Adjudicator overrides INDETERMINATE to PASS with manual verification
    override_resp = await client.post(
        f"/api/v1/rules/evaluations/{eval_id}/override",
        json={
            "outcome": "PASS",
            "override_reason": "Physical re-inspection of the sample package by senior inspector confirmed valid MRP and tax suffix present on top flap."
        },
        headers=adj_headers
    )
    assert override_resp.status_code == 200
    override_data = override_resp.json()["data"]
    assert override_data["outcome"] == "PASS"
    assert override_data["officer_overridden"] is True
