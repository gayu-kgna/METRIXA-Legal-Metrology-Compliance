import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rule_definition import RuleDefinition
from app.models.rule_evaluation import RuleEvaluation
from app.models.inspection import Inspection
from app.models.product import Product
from app.models.surface import InspectionSurface
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.entity_run import EntityParsingRun
from app.models.audit_log import AuditLog
from app.models.enums import RuleOutcome, FieldType, InspectionOverallStatus
from app.services.rules.models import (
    EvaluationContext,
    RuleEvaluationResult,
    InspectionComplianceSummary,
)
from app.services.rules.applicability import RuleApplicabilityEvaluator
from app.services.rules.evaluators import DeterministicEvaluator
from app.services.rules.registry import RuleRegistry

class DeterministicRuleEngine:
    """
    Deterministic Legal Metrology Compliance Rule Engine.
    Executes versioned, declarative statutory rules against structured observations.
    Ensures complete explainability, traceability, and strict immutability.
    AI/OCR assists perception; this engine alone produces legal compliance verdicts.
    """

    async def evaluate_inspection(
        self,
        db: AsyncSession,
        inspection: Inspection,
        rule_set_version: Optional[str] = None,
        rule_codes: Optional[List[str]] = None,
        include_test_rules: bool = False,
        actor_id: Optional[uuid.UUID] = None,
    ) -> InspectionComplianceSummary:
        """
        Execute deterministic legal rule evaluation for an inspection.
        """
        # 1. Ensure authoritative rules are seeded in database
        await RuleRegistry.seed_rules(db, include_test_rules=include_test_rules)

        # 2. Query applicable RuleDefinitions
        authoritative_codes = [r["rule_code"] for r in RuleRegistry.AUTHORITATIVE_RULES]
        target_rule_codes = rule_codes if rule_codes else authoritative_codes

        query = select(RuleDefinition).where(RuleDefinition.is_active == True)
        if not include_test_rules:
            query = query.where(RuleDefinition.is_test_rule == False)
        if target_rule_codes:
            query = query.where(RuleDefinition.rule_code.in_(target_rule_codes))

        rules = []
        if rule_set_version:
            v_query = query.where(RuleDefinition.version == rule_set_version)
            v_res = await db.execute(v_query.order_by(RuleDefinition.rule_code.asc(), RuleDefinition.version.desc()))
            rules = v_res.scalars().all()

        if not rules:
            # Fallback to latest active versions if requested version not matched or not provided
            rules_result = await db.execute(query.order_by(RuleDefinition.rule_code.asc(), RuleDefinition.version.desc()))
            rules = rules_result.scalars().all()

        # If duplicate versions exist for a rule_code, select latest version
        selected_rules: List[RuleDefinition] = []
        seen_codes = set()
        for r in rules:
            if r.rule_code not in seen_codes:
                selected_rules.append(r)
                seen_codes.add(r.rule_code)

        # 3. Retrieve inspection context & evidence
        # Halt execution if any entity parsing run failed (Requirement 4)
        failed_entity_runs = await db.execute(
            select(EntityParsingRun)
            .where(
                EntityParsingRun.inspection_id == inspection.id,
                EntityParsingRun.status == "FAILED",
            )
        )
        if failed_entity_runs.scalars().first():
            raise ValueError(
                "Cannot evaluate deterministic rules: One or more entity parsing runs failed for this inspection. "
                "Downstream rule evaluation has been halted. Resolve the entity parsing error and re-run entity parsing."
            )

        prod_res = await db.execute(select(Product).where(Product.id == inspection.product_id))
        product = prod_res.scalar_one_or_none()

        surf_res = await db.execute(select(InspectionSurface).where(InspectionSurface.inspection_id == inspection.id))
        surfaces = surf_res.scalars().all()

        obs_res = await db.execute(
            select(Observation).where(
                Observation.inspection_id == inspection.id,
                Observation.is_latest == True,
            )
        )
        observations = obs_res.scalars().all()

        # Group observations by FieldType
        obs_by_type: Dict[FieldType, List[Observation]] = {}
        for o in observations:
            obs_by_type.setdefault(o.field_type, []).append(o)

        geom_res = await db.execute(select(PDPGeometry).where(PDPGeometry.inspection_id == inspection.id))
        geometries = geom_res.scalars().all()

        eval_timestamp = datetime.now(timezone.utc)
        context = EvaluationContext(
            inspection=inspection,
            product=product,
            observations_by_type=obs_by_type,
            surfaces=surfaces,
            pdp_geometries=geometries,
            evaluation_timestamp=eval_timestamp,
        )

        evaluation_run_id = uuid.uuid4()
        evaluation_results: List[RuleEvaluationResult] = []
        eval_db_records: List[RuleEvaluation] = []

        pass_count = 0
        fail_count = 0
        review_count = 0
        indeterminate_count = 0
        na_count = 0

        # 4. Evaluate each rule deterministically
        for rule in selected_rules:
            # Step A: Evaluate Applicability
            applicability = RuleApplicabilityEvaluator.evaluate_applicability(rule, context)

            if not applicability.is_applicable:
                res = RuleEvaluationResult(
                    rule_definition_id=rule.id,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    outcome=RuleOutcome.NOT_APPLICABLE,
                    legal_rationale=applicability.reason,
                    statutory_citation=f"{rule.legal_act} - {rule.rule_reference} (Not Applicable)",
                    evidence_references={"applicability": applicability.model_dump()},
                    applicability_result=applicability.model_dump(),
                    evaluated_at=eval_timestamp,
                )
                na_count += 1
            else:
                # Step B: Evaluate Rule Condition
                res = DeterministicEvaluator.evaluate(rule, context, applicability)

                if res.outcome == RuleOutcome.PASS:
                    pass_count += 1
                elif res.outcome == RuleOutcome.FAIL:
                    fail_count += 1
                elif res.outcome == RuleOutcome.REVIEW:
                    review_count += 1
                elif res.outcome == RuleOutcome.INDETERMINATE:
                    indeterminate_count += 1
                elif res.outcome == RuleOutcome.NOT_APPLICABLE:
                    na_count += 1

            evaluation_results.append(res)

            # Construct persistent RuleEvaluation model
            db_eval = RuleEvaluation(
                id=uuid.uuid4(),
                inspection_id=inspection.id,
                rule_definition_id=rule.id,
                outcome=res.outcome,
                legal_rationale=res.legal_rationale,
                statutory_citation=res.statutory_citation,
                rule_version=rule.version,
                evidence_references=res.evidence_references,
                applicability_result=res.applicability_result,
                evaluation_run_id=evaluation_run_id,
                officer_overridden=False,
                evaluated_at=eval_timestamp,
            )
            db.add(db_eval)
            eval_db_records.append(db_eval)

        # 5. Record immutable AuditLog
        audit_log = AuditLog(
            id=uuid.uuid4(),
            inspection_id=inspection.id,
            user_id=actor_id,
            action="DETERMINISTIC_RULES_EVALUATED",
            entity_type="Inspection",
            entity_id=str(inspection.id),
            previous_state={},
            new_state={
                "evaluation_run_id": str(evaluation_run_id),
                "total_rules": len(selected_rules),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "review_count": review_count,
                "indeterminate_count": indeterminate_count,
                "not_applicable_count": na_count,
            },
            justification=f"Deterministic rule engine evaluation completed for inspection {inspection.inspection_number}",
            performed_at=eval_timestamp,
        )
        db.add(audit_log)

        # Derive inspection overall status from deterministic evaluation results
        if fail_count > 0:
            inspection.overall_status = InspectionOverallStatus.NON_COMPLIANT
            canonical_verdict = "NON_COMPLIANT"
        elif review_count > 0:
            inspection.overall_status = InspectionOverallStatus.IN_REVIEW
            canonical_verdict = "REVIEW_REQUIRED"
        elif indeterminate_count > 0:
            inspection.overall_status = InspectionOverallStatus.INDETERMINATE
            canonical_verdict = "INDETERMINATE"
        elif pass_count > 0:
            inspection.overall_status = InspectionOverallStatus.COMPLIANT
            canonical_verdict = "COMPLIANT"
        else:
            inspection.overall_status = InspectionOverallStatus.INDETERMINATE
            canonical_verdict = "INDETERMINATE"

        db.add(inspection)
        await db.commit()
        await db.refresh(inspection)

        return InspectionComplianceSummary(
            inspection_id=inspection.id,
            evaluation_run_id=evaluation_run_id,
            evaluated_at=eval_timestamp,
            rule_set_version=rule_set_version,
            total_rules=len(selected_rules),
            pass_count=pass_count,
            fail_count=fail_count,
            review_count=review_count,
            indeterminate_count=indeterminate_count,
            not_applicable_count=na_count,
            overall_verdict=canonical_verdict,
            evaluations=evaluation_results,
        )
