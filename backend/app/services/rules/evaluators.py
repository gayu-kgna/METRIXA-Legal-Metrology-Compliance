import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models.rule_definition import RuleDefinition
from app.models.enums import RuleOutcome, FieldType, ObservationStatus
from app.models.observation import Observation
from app.services.rules.models import EvaluationContext, RuleEvaluationResult, ApplicabilityResult

class DeterministicEvaluator:
    """
    Deterministic Legal Metrology Rule Evaluator.
    Dispatches declarative statutory evaluation logic by category.
    Strictly deterministic: identical inputs and rule versions always produce identical verdicts.
    AI/OCR aids perception; this evaluator deterministically establishes compliance.
    """

    @classmethod
    def evaluate(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        eval_logic = rule.evaluation_logic or {}
        logic_type = eval_logic.get("type", "MANDATORY_DECLARATION_PRESENCE")

        if rule.rule_code == "PCR-2011-R06-1-B" or logic_type in ("GENERIC_NAME", "GENERIC_COMMODITY_NAME"):
            return cls._evaluate_generic_name(rule, context, applicability)
        elif logic_type == "MANDATORY_DECLARATION_PRESENCE":
            return cls._evaluate_mandatory_presence(rule, context, applicability)
        elif logic_type == "NET_QUANTITY_DECLARATION":
            return cls._evaluate_net_quantity(rule, context, applicability)
        elif logic_type == "MRP_DECLARATION":
            return cls._evaluate_mrp(rule, context, applicability)
        elif logic_type == "MANUFACTURER_PACKER_IMPORTER":
            return cls._evaluate_party_declaration(rule, context, applicability)
        elif logic_type == "CONSUMER_CARE":
            return cls._evaluate_consumer_care(rule, context, applicability)
        elif logic_type == "COUNTRY_OF_ORIGIN":
            return cls._evaluate_country_of_origin(rule, context, applicability)
        elif logic_type == "UNIT_SALE_PRICE":
            return cls._evaluate_unit_sale_price(rule, context, applicability)
        elif logic_type == "DATE_DECLARATION":
            return cls._evaluate_date_declaration(rule, context, applicability)
        elif logic_type == "PDP_GEOMETRY_PLACEMENT_AND_SIZE":
            return cls._evaluate_pdp_geometry(rule, context, applicability)
        else:
            return cls._evaluate_mandatory_presence(rule, context, applicability)

    # -------------------------------------------------------------------------
    # Category 1: Mandatory Declaration Presence
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_mandatory_presence(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        req_fields = (rule.evidence_requirements or {}).get("required_fields", [])
        evidence_refs: Dict[str, Any] = {
            "required_fields": req_fields,
            "observation_ids": [],
            "source_region_ids": [],
            "bounding_boxes": [],
        }

        matched_obs: List[Observation] = []
        missing_fields: List[str] = []
        conflicts: List[str] = []

        for f_name in req_fields:
            try:
                ft = FieldType(f_name)
            except ValueError:
                ft = None

            if not ft:
                continue

            all_obs = context.get_all_observations(ft)
            active_obs = [o for o in all_obs if o.is_latest]

            if not active_obs:
                missing_fields.append(f_name)
            else:
                for o in active_obs:
                    evidence_refs["observation_ids"].append(str(o.id))
                    if o.ocr_region_id:
                        evidence_refs["source_region_ids"].append(str(o.ocr_region_id))
                    if o.bounding_box:
                        evidence_refs["bounding_boxes"].append(o.bounding_box)

                    if o.status == ObservationStatus.CONFLICTING:
                        conflicts.append(f"Observation for {f_name} has conflicting readings: '{o.raw_value}'")

                matched_obs.extend(active_obs)

        # 1. Conflicting Evidence Check
        if conflicts:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.REVIEW,
                legal_rationale=f"Material ambiguity / conflicting readings detected for mandatory declaration: {'; '.join(conflicts)}. Adjudication required.",
                statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # 2. Low Confidence / Occlusion Check
        low_conf_obs = [o for o in matched_obs if o.confidence < 0.50]
        if low_conf_obs:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale=f"Evidence detected with insufficient OCR confidence ({low_conf_obs[0].confidence:.2f}) for field {low_conf_obs[0].field_type.value}. Cannot definitively establish compliance.",
                statutory_citation=f"{rule.legal_act} - {rule.rule_reference} (Evidence Insufficient)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # 3. Missing Fields Check (Absence vs. Indeterminate)
        if missing_fields:
            if len(context.surfaces) == 0:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale=f"Cannot establish presence or absence of mandatory field(s) {', '.join(missing_fields)} due to lack of package surface evidence.",
                    statutory_citation=f"{rule.legal_act} - {rule.rule_reference} (Missing Surface Evidence)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            elif not context.has_pdp_surface and not context.has_back_surface and not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale=f"Cannot establish presence or absence of mandatory field(s) {', '.join(missing_fields)}: Primary package display surfaces (FRONT_PDP, BACK) were not submitted.",
                    statutory_citation=f"{rule.legal_act} - {rule.rule_reference} (Primary Surfaces Not Submitted)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            elif not context.has_back_surface and not context.has_single_surface_comprehensive_label and "PRODUCT_NAME" in missing_fields:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Generic/common commodity name not observable on submitted FRONT_PDP. Declaration is permitted on package informational panels (e.g. BACK), which were not submitted for this inspection.",
                    statutory_citation=f"{rule.legal_act} - {rule.rule_reference} (Informational Surface Not Submitted)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            else:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.FAIL,
                    legal_rationale=f"Mandatory declaration absent on inspected package surfaces. Missing required statutory field(s): {', '.join(missing_fields)}.",
                    statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )

        # 4. Compliant PASS
        obs_summaries = [f"{o.field_type.value}: '{o.raw_value}'" for o in matched_obs]
        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Mandatory declaration verified present and satisfied on packaging: {'; '.join(obs_summaries)}.",
            statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 1b: Generic or Common Commodity Name (Rule 6(1)(b))
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_generic_name(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        gen_obs = context.get_latest_observation(FieldType.GENERIC_NAME)
        # Fallback to PRODUCT_NAME if GENERIC_NAME is absent
        prod_obs = context.get_latest_observation(FieldType.PRODUCT_NAME)

        target_obs = gen_obs or prod_obs

        evidence_refs: Dict[str, Any] = {
            "required_fields": ["GENERIC_NAME"],
            "observation_ids": [],
            "source_region_ids": [],
            "bounding_boxes": [],
        }

        if target_obs:
            evidence_refs["observation_ids"].append(str(target_obs.id))
            if target_obs.ocr_region_id:
                evidence_refs["source_region_ids"].append(str(target_obs.ocr_region_id))
            if target_obs.bounding_box:
                evidence_refs["bounding_boxes"].append(target_obs.bounding_box)

            decl_name = target_obs.raw_value
            if target_obs.normalized_value and target_obs.normalized_value.get("generic_name"):
                decl_name = target_obs.normalized_value.get("generic_name")
            elif target_obs.normalized_value and target_obs.normalized_value.get("name"):
                decl_name = target_obs.normalized_value.get("name")

            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.PASS,
                legal_rationale=f"Generic or common commodity name declaration verified: '{decl_name}'. Satisfies statutory commodity declaration under Rule 6(1)(b).",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(b) (Generic Commodity Name)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        if not context.has_back_surface and not context.has_single_surface_comprehensive_label:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale="Generic or common commodity name not observable on submitted package surfaces. Informational surfaces (BACK) were not submitted for this inspection.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(b) (Informational Surface Not Submitted)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.FAIL,
            legal_rationale="Generic or common commodity name absent on inspected package surfaces under Rule 6(1)(b).",
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(b) (Commodity Name Absent)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 2: Net Quantity & Multi-pack Rules
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_net_quantity(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        if not context.has_pdp_surface:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale="Principal Display Panel (FRONT_PDP) was not submitted for inspection. Under Rule 6(1)(c) of Legal Metrology (Packaged Commodities) Rules, 2011, statutory net quantity declaration must appear on the Principal Display Panel.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(c) (PDP Surface Not Submitted)",
                evidence_references={"required_fields": ["NET_QUANTITY"], "observation_ids": []},
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        pdp_surfaces = [s for s in context.surfaces if getattr(s.surface_type, "value", str(s.surface_type)) == "FRONT_PDP"]
        pdp_surface_ids = {s.id for s in pdp_surfaces}
        all_qty_obs = context.get_all_observations(FieldType.NET_QUANTITY)
        pdp_qty_obs = [o for o in all_qty_obs if o.is_latest and (o.surface_id in pdp_surface_ids or o.surface_id is None)]
        obs = pdp_qty_obs[0] if pdp_qty_obs else None
        if not obs:
            return cls._evaluate_mandatory_presence(rule, context, applicability)

        evidence_refs = {
            "observation_ids": [str(obs.id)],
            "source_region_ids": [str(obs.ocr_region_id)] if obs.ocr_region_id else [],
            "bounding_boxes": [obs.bounding_box] if obs.bounding_box else [],
        }

        norm = obs.normalized_value or {}
        unit = (norm.get("unit") or norm.get("base_unit") or "").lower()
        mag = norm.get("value") if norm.get("value") is not None else norm.get("magnitude", 0.0)

        # Standard statutory metric units under Rule 12 of PCMR 2011
        valid_units = {"g", "gm", "gram", "grams", "kg", "kilogram", "ml", "millilitre", "l", "ltr", "liter", "litre", "m", "cm", "mm", "n", "u", "pc", "pcs", "units"}
        if unit not in valid_units:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale=f"Net quantity unit '{unit}' is not a standard statutory metric unit prescribed under Rule 12 of Legal Metrology (Packaged Commodities) Rules, 2011.",
                statutory_citation=f"{rule.legal_act} - Rule 12 (Units of Weight or Measure)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        if mag <= 0:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale=f"Net quantity magnitude ({mag}) must be greater than zero.",
                statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        rationale = f"Statutory net quantity declaration verified: {mag} {unit}"
        if (norm.get("count") and norm.get("count") > 1) or norm.get("is_multi_pack"):
            count = norm.get("count") or norm.get("item_count")
            ind_qty = norm.get("individual_quantity") or norm.get("item_quantity")
            ind_unit = norm.get("individual_unit") or unit
            tot_qty = norm.get("total_quantity") or mag
            tot_unit = norm.get("total_unit") or unit
            rationale += f" (Multi-pack verified: {count} packs of {ind_qty}{ind_unit}, total {tot_qty}{tot_unit})"

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=rationale,
            statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 3: MRP & Tax Inclusivity Rules
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_mrp(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        all_mrp_obs = context.get_all_observations(FieldType.MRP)
        active_mrp_obs = [o for o in all_mrp_obs if o.is_latest]

        if not active_mrp_obs:
            if not context.has_back_surface and not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Maximum Retail Price (MRP) declaration not observable on submitted surfaces. The primary informational panel (BACK) and batch coding areas were not submitted for inspection.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(da) (Informational Surfaces Not Submitted)",
                    evidence_references={"required_fields": ["MRP"], "observation_ids": []},
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            elif not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Maximum Retail Price (MRP) declaration is not confidently observable from OCR perception evidence. Under Legal Metrology enforcement rules, unobserved pricing without positive proof of omission cannot be confirmed absent; physical inspection or adjudication required.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(da) (Declaration Not Confidently Observable)",
                    evidence_references={"required_fields": ["MRP"], "observation_ids": []},
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            return cls._evaluate_mandatory_presence(rule, context, applicability)

        amounts = set()
        for o in active_mrp_obs:
            norm = o.normalized_value or {}
            amt = norm.get("value") if norm.get("value") is not None else norm.get("amount")
            if amt is not None:
                amounts.add(amt)

        evidence_refs = {
            "observation_ids": [str(o.id) for o in active_mrp_obs],
            "source_region_ids": [str(o.ocr_region_id) for o in active_mrp_obs if o.ocr_region_id],
            "bounding_boxes": [o.bounding_box for o in active_mrp_obs if o.bounding_box],
        }

        if len(amounts) > 1 or any(o.status == ObservationStatus.CONFLICTING for o in active_mrp_obs):
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.REVIEW,
                legal_rationale=f"Multiple conflicting readings or unadjudicated character confusion detected for Maximum Retail Price ({sorted(list(amounts)) if len(amounts) > 1 else 'Conflicting status'}). Statutory rules prohibit dual pricing or ambiguous retail prices.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(da) (Single Retail Price)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        obs = active_mrp_obs[0]
        norm = obs.normalized_value or {}
        amt = norm.get("value") if norm.get("value") is not None else norm.get("amount", 0.0)
        curr = norm.get("currency", "INR")
        is_tax_incl = norm.get("includes_taxes") if "includes_taxes" in norm else norm.get("is_tax_inclusive", False)

        if amt <= 0:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale=f"Maximum Retail Price must be greater than zero. Detected: {amt}.",
                statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # Tax inclusivity check under Rule 6(1)(da)
        if rule.parameters.get("require_tax_inclusive", True) and not is_tax_incl:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale=f"Maximum Retail Price ({curr} {amt}) is missing the mandatory statutory clause 'inclusive of all taxes' or 'incl. of all taxes'.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(da) (Tax Inclusivity Requirement)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Statutory Maximum Retail Price verified: {curr} {amt:.2f} inclusive of all taxes.",
            statutory_citation=f"{rule.legal_act} - {rule.rule_reference}",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 4: Manufacturer / Packer / Importer Rules
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_party_declaration(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        mfg_obs = context.get_latest_observation(FieldType.MANUFACTURER_NAME)
        pkr_obs = context.get_latest_observation(FieldType.PACKER_NAME)
        imp_obs = context.get_latest_observation(FieldType.IMPORTER_NAME)

        evidence_refs: Dict[str, Any] = {"observation_ids": [], "source_region_ids": [], "bounding_boxes": []}
        for o in [mfg_obs, pkr_obs, imp_obs]:
            if o:
                evidence_refs["observation_ids"].append(str(o.id))
                if o.ocr_region_id:
                    evidence_refs["source_region_ids"].append(str(o.ocr_region_id))
                if o.bounding_box:
                    evidence_refs["bounding_boxes"].append(o.bounding_box)

        # If imported commodity rule, require importer
        if rule.parameters.get("require_importer", False):
            if not imp_obs:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.FAIL,
                    legal_rationale="Imported commodity must bear the name and complete address of the importer under Rule 6(1)(a). Importer declaration is absent.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(a) (Importer Declaration)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.PASS,
                legal_rationale=f"Importer declaration verified: '{imp_obs.raw_value}'.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(a)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # Manufacturer, Packer, or Importer required under Rule 6(1)(a)
        if not mfg_obs and not pkr_obs and not imp_obs:
            if not context.has_back_surface and not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Manufacturer/Packer declaration not observable on submitted surfaces. The primary informational panel (BACK) was not submitted for inspection.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(a) (Informational Surfaces Not Submitted)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale="Packaged commodity must bear the name and complete address of the manufacturer, packer, or importer under Rule 6(1)(a). All are absent on inspected package surfaces.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(a) (Manufacturer/Packer/Importer Declaration)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        declared_party = mfg_obs.raw_value if mfg_obs else (pkr_obs.raw_value if pkr_obs else imp_obs.raw_value)
        party_role = "Manufacturer" if mfg_obs else ("Packer" if pkr_obs else "Importer")
        is_marketed_by = False
        if mfg_obs and mfg_obs.normalized_value:
            if mfg_obs.normalized_value.get("entity_type") in ("MARKETED_BY", "MARKETER") or (
                isinstance(mfg_obs.raw_value, str) and re.search(r"^(?:marketed|mkt\.?)\s*by", mfg_obs.raw_value, re.IGNORECASE)
            ):
                party_role = "Marketed By"
                is_marketed_by = True
                if mfg_obs.normalized_value.get("name"):
                    declared_party = mfg_obs.normalized_value.get("name")

        if is_marketed_by:
            rationale = f"Marketed By declaration observed: '{declared_party}'. Under Rule 6(1)(a) administrative acceptance, marketer declaration is observed on inspected packaging."
        else:
            rationale = f"{party_role} declaration verified: '{declared_party}'."

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=rationale,
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(a)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 5: Consumer Care Details
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_consumer_care(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        phone_obs = context.get_latest_observation(FieldType.CONSUMER_CARE_PHONE)
        email_obs = context.get_latest_observation(FieldType.CONSUMER_CARE_EMAIL)
        addr_obs = context.get_latest_observation(FieldType.CONSUMER_CARE_ADDRESS)

        evidence_refs: Dict[str, Any] = {"observation_ids": [], "source_region_ids": [], "bounding_boxes": []}
        for o in [phone_obs, email_obs, addr_obs]:
            if o:
                evidence_refs["observation_ids"].append(str(o.id))
                if o.ocr_region_id:
                    evidence_refs["source_region_ids"].append(str(o.ocr_region_id))
                if o.bounding_box:
                    evidence_refs["bounding_boxes"].append(o.bounding_box)

        # Rule 6(1)(e): Must bear consumer care contact (telephone or email or address)
        if not phone_obs and not email_obs and not addr_obs:
            if not context.has_back_surface and not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Consumer care contact details not observable on submitted surfaces. The primary informational panel (BACK) was not submitted for inspection.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(e) (Informational Surfaces Not Submitted)",
                    evidence_references=evidence_refs,
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale="Consumer care details absent. Package must declare telephone number, email, or physical address for consumer complaints under Rule 6(1)(e). Absent on inspected package surfaces.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(e) (Consumer Care Information)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        channels = []
        if phone_obs:
            channels.append(f"Phone: {phone_obs.raw_value}")
        if email_obs:
            channels.append(f"Email: {email_obs.raw_value}")
        if addr_obs:
            channels.append(f"Address: {addr_obs.raw_value}")

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Consumer care contact details verified: {'; '.join(channels)}.",
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(e)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 6: Country of Origin
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_country_of_origin(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        obs = context.get_latest_observation(FieldType.COUNTRY_OF_ORIGIN)
        if not obs:
            return cls._evaluate_mandatory_presence(rule, context, applicability)

        evidence_refs = {
            "observation_ids": [str(obs.id)],
            "source_region_ids": [str(obs.ocr_region_id)] if obs.ocr_region_id else [],
            "bounding_boxes": [obs.bounding_box] if obs.bounding_box else [],
        }

        norm = obs.normalized_value or {}
        country = norm.get("country", obs.raw_value).strip()

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Country of origin declaration verified: '{country}'.",
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(f) (Country of Origin Declaration)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 7: Unit Sale Price (USP)
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_unit_sale_price(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        obs = context.get_latest_observation(FieldType.UNIT_SALE_PRICE)
        if not obs:
            return cls._evaluate_mandatory_presence(rule, context, applicability)

        evidence_refs = {
            "observation_ids": [str(obs.id)],
            "source_region_ids": [str(obs.ocr_region_id)] if obs.ocr_region_id else [],
            "bounding_boxes": [obs.bounding_box] if obs.bounding_box else [],
        }

        norm = obs.normalized_value or {}
        usp_val = norm.get("value")
        usp_unit = norm.get("unit")

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Unit Sale Price verified: '{obs.raw_value}' ({usp_val} per {usp_unit}).",
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(g) (Unit Sale Price)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 8: Date Declarations & Ambiguity
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_date_declaration(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        # Check manufacturing, packing, or import date observations
        mfg_obs = context.get_latest_observation(FieldType.MFG_DATE) or context.get_latest_observation(FieldType.DATE_OF_MANUFACTURE)
        pkd_obs = context.get_latest_observation(FieldType.DATE_OF_PACKING)
        date_obs = mfg_obs or pkd_obs

        if not date_obs:
            if not context.has_back_surface and not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Date of manufacture/packing declaration not observable on submitted surfaces. The primary informational panel (BACK) and batch coding areas were not submitted for inspection.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(d) (Informational Surfaces Not Submitted)",
                    evidence_references={"required_fields": ["MFG_DATE"], "observation_ids": []},
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            elif not context.has_single_surface_comprehensive_label:
                return RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.INDETERMINATE,
                    legal_rationale="Date of manufacture/packing declaration is not confidently observable from OCR perception evidence. Under Legal Metrology enforcement rules, unobserved batch coding without positive proof of omission cannot be confirmed absent; physical inspection or adjudication required.",
                    statutory_citation=f"{rule.legal_act} - Rule 6(1)(d) (Declaration Not Confidently Observable)",
                    evidence_references={"required_fields": ["MFG_DATE"], "observation_ids": []},
                    applicability_result=applicability.model_dump(),
                    evaluated_at=context.evaluation_timestamp,
                )
            return cls._evaluate_mandatory_presence(rule, context, applicability)

        evidence_refs = {
            "observation_ids": [str(date_obs.id)],
            "source_region_ids": [str(date_obs.ocr_region_id)] if date_obs.ocr_region_id else [],
            "bounding_boxes": [date_obs.bounding_box] if date_obs.bounding_box else [],
        }

        norm = date_obs.normalized_value or {}
        
        # Ambiguity check: if both day and month are <= 12 and ambiguous
        if norm.get("is_ambiguous", False):
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.REVIEW,
                legal_rationale=f"Date declaration '{date_obs.raw_value}' is materially ambiguous (cannot distinguish day from month). Human adjudication required.",
                statutory_citation=f"{rule.legal_act} - Rule 6(1)(d) (Date Format Clarity)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        iso_date = norm.get("date_iso") or norm.get("iso_date") or date_obs.raw_value
        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Date of manufacture/packing verified: '{date_obs.raw_value}' (Standardized: {iso_date}).",
            statutory_citation=f"{rule.legal_act} - Rule 6(1)(d)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )

    # -------------------------------------------------------------------------
    # Category 9: PDP Geometry, Placement & Font Height (Calibrated)
    # -------------------------------------------------------------------------
    @classmethod
    def _evaluate_pdp_geometry(
        cls,
        rule: RuleDefinition,
        context: EvaluationContext,
        applicability: ApplicabilityResult,
    ) -> RuleEvaluationResult:
        front_geom = context.get_front_pdp_geometry()
        evidence_refs: Dict[str, Any] = {
            "geometry_ids": [str(front_geom.id)] if front_geom else [],
            "observation_ids": [],
            "source_region_ids": [],
            "bounding_boxes": [],
        }

        # 1. Authentic Physical Calibration Invariance Check
        if not front_geom or not front_geom.has_calibration:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale="Statutory numeral and letter height requirements (Rule 7, Table 1) require physical calibration in millimeters. The inspected packaging image lacks authentic physical calibration; pixel measurements cannot be fabricated into physical dimensions without proof.",
                statutory_citation=f"{rule.legal_act} - Rule 7 (Minimum Height of Numerals and Letters)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # 2. Placement and Height Evaluation (When calibrated)
        params = rule.parameters or {}
        target_field = params.get("target_field", "NET_QUANTITY")
        min_height_mm = params.get("min_height_mm", 2.0)

        # Retrieve text placement for target field from declarations_geometry
        decl_geoms = front_geom.declarations_geometry.get("declarations", [])
        matched_decl = None
        for d in decl_geoms:
            if d.get("field_type") == target_field:
                matched_decl = d
                break

        if not matched_decl:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale=f"Declaration geometry for '{target_field}' could not be isolated on Principal Display Panel.",
                statutory_citation=f"{rule.legal_act} - Rule 7",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        measured_height_mm = matched_decl.get("estimated_physical_text_height_mm") or matched_decl.get("text_height_mm")
        quadrant = matched_decl.get("quadrant", "UNKNOWN")

        if measured_height_mm is None:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.INDETERMINATE,
                legal_rationale=f"Measured height in millimeters is not available for {target_field}.",
                statutory_citation=f"{rule.legal_act} - Rule 7",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        # Check font height against minimum statutory requirement
        if measured_height_mm < min_height_mm:
            return RuleEvaluationResult(
                rule_definition_id=rule.id,
                rule_code=rule.rule_code,
                rule_version=rule.version,
                outcome=RuleOutcome.FAIL,
                legal_rationale=f"Measured text height for {target_field} ({measured_height_mm:.2f} mm in quadrant {quadrant}) fails statutory minimum threshold of {min_height_mm:.2f} mm under Rule 7.",
                statutory_citation=f"{rule.legal_act} - Rule 7 (Minimum Character Height)",
                evidence_references=evidence_refs,
                applicability_result=applicability.model_dump(),
                evaluated_at=context.evaluation_timestamp,
            )

        return RuleEvaluationResult(
            rule_definition_id=rule.id,
            rule_code=rule.rule_code,
            rule_version=rule.version,
            outcome=RuleOutcome.PASS,
            legal_rationale=f"Declaration placement and character height verified on PDP: {measured_height_mm:.2f} mm >= minimum {min_height_mm:.2f} mm (Quadrant: {quadrant}).",
            statutory_citation=f"{rule.legal_act} - Rule 7 (Numeral and Letter Height)",
            evidence_references=evidence_refs,
            applicability_result=applicability.model_dump(),
            evaluated_at=context.evaluation_timestamp,
        )
