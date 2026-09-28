from typing import Dict, Any, List
from app.models.rule_definition import RuleDefinition
from app.models.enums import FieldType
from app.services.rules.models import EvaluationContext, ApplicabilityResult

class RuleApplicabilityEvaluator:
    """
    Deterministic Legal Rule Applicability Evaluator.
    Evaluates whether a statutory rule applies to a specific inspection context
    BEFORE evaluating compliance conditions.
    Decoupled from compliance verdicts: applicability determines IF a rule applies,
    not whether the packaging passes or fails.
    """

    @classmethod
    def evaluate_applicability(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
    ) -> ApplicabilityResult:
        conditions = rule.applicability_conditions or {}
        exemptions = rule.exemptions or {}
        eval_time = context.evaluation_timestamp

        # 1. Temporal Validity Check
        if rule.effective_from and eval_time < rule.effective_from:
            return ApplicabilityResult(
                is_applicable=False,
                reason=f"Rule {rule.rule_code} (v{rule.version}) is not yet effective. Effective from: {rule.effective_from.isoformat()}.",
                conditions_evaluated={"effective_from": rule.effective_from.isoformat(), "eval_time": eval_time.isoformat()}
            )

        if rule.effective_to and eval_time > rule.effective_to:
            return ApplicabilityResult(
                is_applicable=False,
                reason=f"Rule {rule.rule_code} (v{rule.version}) has expired. Effective to: {rule.effective_to.isoformat()}.",
                conditions_evaluated={"effective_to": rule.effective_to.isoformat(), "eval_time": eval_time.isoformat()}
            )

        if not rule.is_active:
            return ApplicabilityResult(
                is_applicable=False,
                reason=f"Rule {rule.rule_code} is currently deactivated in the rule registry.",
                conditions_evaluated={"is_active": False}
            )

        # 2. Scope & Commodity Type Applicability
        scope = conditions.get("commodity_scope", "ALL_RETAIL_PACKAGES")
        
        # Check imported commodity requirement
        if scope == "IMPORTED_COMMODITY" or conditions.get("requires_imported", False):
            is_imported = False
            if context.product and context.product.metadata_json:
                is_imported = context.product.metadata_json.get("is_imported", False) or context.product.commodity_type == "IMPORTED"
            
            # Also check if importer observation exists or country of origin is non-India
            importer_obs = context.get_latest_observation(FieldType.IMPORTER_NAME)
            origin_obs = context.get_latest_observation(FieldType.COUNTRY_OF_ORIGIN)
            if importer_obs:
                is_imported = True
            elif origin_obs and origin_obs.normalized_value:
                country = origin_obs.normalized_value.get("country", "").strip().lower()
                if country and country not in ["india", "in", "ind"]:
                    is_imported = True

            if not is_imported:
                return ApplicabilityResult(
                    is_applicable=False,
                    reason=f"Rule applies exclusively to imported commodities. Inspected product is domestic.",
                    conditions_evaluated={"commodity_scope": scope, "is_imported": False}
                )

        # 3. Unit Sale Price (USP) Applicability Conditions
        if conditions.get("check_usp_applicability", False):
            # If rule parameters specify minimum package weight/volume threshold
            min_base_qty = rule.parameters.get("min_base_quantity")
            if min_base_qty is not None:
                qty_obs = context.get_latest_observation(FieldType.NET_QUANTITY)
                if not qty_obs or not qty_obs.normalized_value:
                    return ApplicabilityResult(
                        is_applicable=False,
                        reason="Package net quantity is not established on inspected surfaces; mandatory Unit Sale Price threshold (> 1000g/ml) cannot be verified under Rule 6(1)(g).",
                        conditions_evaluated={"check_usp_applicability": True, "qty_observed": False}
                    )
                base_mag = qty_obs.normalized_value.get("base_quantity") if qty_obs.normalized_value.get("base_quantity") is not None else qty_obs.normalized_value.get("base_magnitude")
                base_u = qty_obs.normalized_value.get("base_unit") or qty_obs.normalized_value.get("unit")
                if base_mag is not None and base_mag <= min_base_qty:
                    return ApplicabilityResult(
                        is_applicable=False,
                        reason=f"Package net quantity ({base_mag} {base_u}) does not exceed the statutory threshold ({min_base_qty}) for mandatory Unit Sale Price declaration.",
                        conditions_evaluated={"package_quantity": base_mag, "threshold": min_base_qty}
                    )

        # 4. Packaging Surface / PDP Placement Applicability
        requires_front_pdp = conditions.get("requires_front_pdp", False)
        if requires_front_pdp:
            front_geom = context.get_front_pdp_geometry()
            if not front_geom:
                # If no PDP surface was submitted/detected for this inspection
                return ApplicabilityResult(
                    is_applicable=False,
                    reason="Rule applies specifically to Principal Display Panel (FRONT_PDP), but no FRONT_PDP surface is present in this inspection.",
                    conditions_evaluated={"requires_front_pdp": True, "front_pdp_found": False}
                )

        # 5. Statutory Exemptions (Rule 26 of PCMR 2011)
        matched_exemptions: List[str] = []

        # Exemption: Packages <= 10g or <= 10ml (Rule 26(a))
        if exemptions.get("exempt_under_10g_or_10ml", False):
            qty_obs = context.get_latest_observation(FieldType.NET_QUANTITY)
            if qty_obs and qty_obs.normalized_value:
                base_mag = qty_obs.normalized_value.get("base_quantity") if qty_obs.normalized_value.get("base_quantity") is not None else qty_obs.normalized_value.get("base_magnitude")
                base_unit = qty_obs.normalized_value.get("base_unit") or qty_obs.normalized_value.get("unit")
                if base_mag is not None and base_mag <= 10.0 and base_unit in ["g", "ml"]:
                    matched_exemptions.append(f"Small package exemption: Net quantity ({base_mag} {base_unit}) <= 10 under Rule 26(a)")

        # Exemption: Institutional / Industrial Consumers
        if exemptions.get("exempt_industrial_consumers", False):
            if context.product and context.product.metadata_json:
                if context.product.metadata_json.get("is_industrial_consumer", False):
                    matched_exemptions.append("Packaged for industrial/institutional consumer under Rule 26")

        if matched_exemptions:
            return ApplicabilityResult(
                is_applicable=False,
                reason=f"Statutory exemption applies: {'; '.join(matched_exemptions)}.",
                conditions_evaluated=conditions,
                exemptions_matched=matched_exemptions,
            )

        return ApplicabilityResult(
            is_applicable=True,
            reason="Rule is legally applicable to this packaged commodity under the Legal Metrology (Packaged Commodities) Rules, 2011.",
            conditions_evaluated=conditions,
            exemptions_matched=[],
        )
