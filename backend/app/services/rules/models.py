import uuid
import enum
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.models.enums import RuleOutcome, FieldType
from app.models.inspection import Inspection
from app.models.product import Product
from app.models.surface import InspectionSurface
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry

class EvidenceSufficiency(str, enum.Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class EvaluationContext:
    """
    Context container for deterministic legal rule evaluation.
    Aggregates inspection details, product specifications, verified observations,
    packaging surfaces, and PDP geometric calibration measurements.
    """
    def __init__(
        self,
        inspection: Inspection,
        product: Optional[Product],
        observations_by_type: Dict[FieldType, List[Observation]],
        surfaces: List[InspectionSurface],
        pdp_geometries: List[PDPGeometry],
        evaluation_timestamp: datetime,
    ):
        self.inspection = inspection
        self.product = product
        self.observations_by_type = observations_by_type
        self.surfaces = surfaces
        self.pdp_geometries = pdp_geometries
        self.evaluation_timestamp = evaluation_timestamp

    def get_latest_observation(self, field_type: FieldType) -> Optional[Observation]:
        obs_list = self.observations_by_type.get(field_type, [])
        for obs in obs_list:
            if obs.is_latest:
                return obs
        return obs_list[0] if obs_list else None

    def get_all_observations(self, field_type: FieldType) -> List[Observation]:
        return self.observations_by_type.get(field_type, [])

    def get_front_pdp_geometry(self) -> Optional[PDPGeometry]:
        for geom in self.pdp_geometries:
            stype = getattr(geom.surface_type, "value", str(geom.surface_type))
            if stype == "FRONT_PDP" or geom.is_pdp_candidate:
                return geom
        return None

    @property
    def submitted_surface_types(self) -> set:
        types = set()
        for s in self.surfaces:
            stype = getattr(s.surface_type, "value", str(s.surface_type))
            types.add(stype)
        return types

    @property
    def has_pdp_surface(self) -> bool:
        return "FRONT_PDP" in self.submitted_surface_types

    @property
    def has_back_surface(self) -> bool:
        return "BACK" in self.submitted_surface_types

    @property
    def has_informational_surface(self) -> bool:
        return bool(self.submitted_surface_types.intersection({"BACK", "LEFT", "RIGHT", "TOP", "BOTTOM"}))

    @property
    def has_single_surface_comprehensive_label(self) -> bool:
        if self.has_informational_surface:
            return False
        return bool(
            self.get_latest_observation(FieldType.MANUFACTURER_NAME)
            or self.get_latest_observation(FieldType.PACKER_NAME)
            or self.get_latest_observation(FieldType.IMPORTER_NAME)
            or self.get_latest_observation(FieldType.CONSUMER_CARE_PHONE)
            or self.get_latest_observation(FieldType.CONSUMER_CARE_EMAIL)
        )

class ApplicabilityResult(BaseModel):
    is_applicable: bool
    reason: str
    conditions_evaluated: Dict[str, Any] = {}
    exemptions_matched: List[str] = []

class RuleEvaluationResult(BaseModel):
    rule_definition_id: uuid.UUID
    rule_code: str
    rule_version: str
    outcome: RuleOutcome
    legal_rationale: str
    statutory_citation: str
    evidence_references: Dict[str, Any] = {}
    applicability_result: Dict[str, Any] = {}
    evaluated_at: datetime

class InspectionComplianceSummary(BaseModel):
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
    overall_verdict: str = "INDETERMINATE"
    evaluations: List[RuleEvaluationResult]
