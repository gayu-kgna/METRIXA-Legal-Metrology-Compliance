import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from app.models.enums import RuleOutcome, RuleSeverity

class RuleDefinitionBase(BaseModel):
    rule_code: str
    version: str = "1.0.0"
    legal_act: str = "Legal Metrology Act, 2009"
    rule_reference: str  # e.g., "Rule 6(1)(e)"
    clause_reference: Optional[str] = None
    title: str
    description: str
    source_document: str  # e.g., "G.S.R. 202(E)"
    source_url: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    jurisdiction: str = "IN"
    category: str = "MANDATORY_DECLARATION"
    is_test_rule: bool = False
    applicability_conditions: Dict[str, Any] = {}
    exemptions: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    evaluation_logic: Dict[str, Any] = {}
    severity: RuleSeverity = RuleSeverity.MANDATORY
    evidence_requirements: Dict[str, Any] = {}
    is_active: bool = True

class RuleDefinitionCreate(RuleDefinitionBase):
    pass

class RuleDefinitionRead(RuleDefinitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class RuleEvaluationBase(BaseModel):
    outcome: RuleOutcome
    legal_rationale: str
    statutory_citation: str
    rule_code: Optional[str] = None
    rule_version: Optional[str] = None
    evidence_references: Dict[str, Any] = {}
    applicability_result: Dict[str, Any] = {}
    evaluation_run_id: Optional[uuid.UUID] = None
    officer_overridden: bool = False
    override_reason: Optional[str] = None

class RuleEvaluationCreate(RuleEvaluationBase):
    inspection_id: uuid.UUID
    rule_definition_id: uuid.UUID
    overriding_officer_id: Optional[uuid.UUID] = None

class RuleEvaluationOverride(BaseModel):
    outcome: RuleOutcome
    override_reason: str

class RuleEvaluationRead(RuleEvaluationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    rule_definition_id: uuid.UUID
    overriding_officer_id: Optional[uuid.UUID] = None
    evaluated_at: datetime
    rule_definition: Optional[RuleDefinitionRead] = None

from pydantic import BaseModel, Field, ConfigDict, model_validator

class RuleEvaluationRequest(BaseModel):
    rule_set_version: Optional[str] = None
    rule_codes: Optional[List[str]] = None
    include_test_rules: bool = False

class InspectionComplianceSummaryResponse(BaseModel):
    inspection_id: uuid.UUID
    evaluation_run_id: uuid.UUID
    evaluated_at: datetime
    rule_set_version: Optional[str] = None
    total_rules: int
    pass_count: int
    fail_count: int
    review_count: int
    indeterminate_count: int
    not_applicable_count: int
    overall_verdict: str = "PENDING"
    evaluations: List[RuleEvaluationRead]

    @model_validator(mode="after")
    def populate_canonical_verdict(self) -> "InspectionComplianceSummaryResponse":
        if self.fail_count > 0:
            self.overall_verdict = "NON_COMPLIANT"
        elif self.review_count > 0:
            self.overall_verdict = "REVIEW_REQUIRED"
        elif self.indeterminate_count > 0:
            self.overall_verdict = "INDETERMINATE"
        elif self.pass_count > 0:
            self.overall_verdict = "COMPLIANT"
        else:
            self.overall_verdict = "INDETERMINATE"
        return self
