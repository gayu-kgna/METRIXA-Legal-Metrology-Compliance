import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator, computed_field, field_validator
from app.models.enums import FieldType, ObservationStatus, CorrectionType, RuleOutcome
from app.schemas.observation import ObservationRead
from app.schemas.rule import RuleEvaluationRead

class BoundingBoxNormalized(BaseModel):
    """
    Normalized spatial bounding box: origin top-left, coordinates in [0, 1].
    Supports both {x, y, width, height} and {xmin, ymin, xmax, ymax} seamlessly.
    Guarantees region remains within image boundaries.
    """
    x: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized X coordinate [0, 1]")
    y: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized Y coordinate [0, 1]")
    width: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized width [0, 1]")
    height: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized height [0, 1]")

    @computed_field
    @property
    def xmin(self) -> float:
        return self.x

    @computed_field
    @property
    def ymin(self) -> float:
        return self.y

    @computed_field
    @property
    def xmax(self) -> float:
        return min(1.0, round(self.x + self.width, 6))

    @computed_field
    @property
    def ymax(self) -> float:
        return min(1.0, round(self.y + self.height, 6))

    @model_validator(mode="before")
    @classmethod
    def convert_minmax(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "xmin" in data and "x" not in data:
                xmin = float(data.get("xmin", 0.0))
                ymin = float(data.get("ymin", 0.0))
                xmax = float(data.get("xmax", 0.0))
                ymax = float(data.get("ymax", 0.0))
                data = dict(data)
                data["x"] = xmin
                data["y"] = ymin
                data["width"] = max(0.0, xmax - xmin)
                data["height"] = max(0.0, ymax - ymin)
        return data

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBoxNormalized":
        if self.x + self.width > 1.0001:
            raise ValueError(f"Bounding box extends beyond right boundary: x({self.x}) + width({self.width}) = {self.x + self.width} > 1.0")
        if self.y + self.height > 1.0001:
            raise ValueError(f"Bounding box extends beyond bottom boundary: y({self.y}) + height({self.height}) = {self.y + self.height} > 1.0")
        return self

class OCRRegionPatchRequest(BaseModel):
    """Payload to modify text and/or spatial bounding box of an OCR region."""
    raw_text: Optional[str] = Field(None, description="Corrected raw text")
    bounding_box: Optional[BoundingBoxNormalized] = Field(None, description="Corrected normalized bounding box")
    reason: str = Field(..., min_length=3, description="Regulatory justification for human correction")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "corrected_text" in data and "raw_text" not in data:
                data["raw_text"] = data["corrected_text"]
            if "corrected_bounding_box" in data and "bounding_box" not in data:
                data["bounding_box"] = data["corrected_bounding_box"]
        return data

class OCRRegionCreateRequest(BaseModel):
    """Payload to create a manual bounding box region."""
    surface_id: uuid.UUID
    raw_text: str = Field(..., min_length=1, description="Text recognized in this manual region")
    bounding_box: BoundingBoxNormalized
    ocr_run_id: Optional[uuid.UUID] = None
    reason: str = Field(..., min_length=3, description="Justification for manually marking region")

class OCRRegionRejectRequest(BaseModel):
    """Payload to reject an OCR region without mutating the historical record."""
    reason: str = Field(..., min_length=3, description="Regulatory justification for rejecting region")

class OCRAdjudicationRead(BaseModel):
    """Audit representation of an OCR adjudication record."""
    id: uuid.UUID
    inspection_id: uuid.UUID
    surface_id: uuid.UUID
    ocr_run_id: Optional[uuid.UUID] = None
    ocr_region_id: Optional[uuid.UUID] = None
    parent_adjudication_id: Optional[uuid.UUID] = None
    correction_type: CorrectionType
    status: str
    original_text: Optional[str] = None
    corrected_text: Optional[str] = None
    original_bounding_box: Dict[str, Any] = Field(default_factory=dict)
    corrected_bounding_box: Dict[str, Any] = Field(default_factory=dict)
    original_confidence: float = 1.0
    reason: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    revision: int = 1
    is_active: bool = True
    adjudicated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdjudicatedOCRRegion(BaseModel):
    """
    Unified representation of an OCR region merged with its active human adjudication state.
    Distinguishes ORIGINAL, CORRECTED, MANUAL, and REJECTED regions.
    """
    id: uuid.UUID
    surface_id: uuid.UUID
    ocr_run_id: Optional[uuid.UUID] = None
    raw_text: str
    original_text: str
    confidence: float
    bounding_box: Dict[str, Any]
    original_bounding_box: Dict[str, Any]
    status: str = "ORIGINAL"  # ORIGINAL, CORRECTED, MANUAL, REJECTED
    correction_type: Optional[str] = None
    is_adjudicated: bool = False
    adjudication_id: Optional[uuid.UUID] = None
    revision: int = 1
    reason: Optional[str] = None
    adjudicated_by: Optional[str] = None
    adjudicated_at: Optional[datetime] = None
    linked_observation_id: Optional[uuid.UUID] = None
    linked_field_type: Optional[str] = None

    @computed_field
    @property
    def effective_text(self) -> str:
        return self.raw_text

    @computed_field
    @property
    def effective_bounding_box(self) -> Dict[str, Any]:
        return self.bounding_box

    @computed_field
    @property
    def is_rejected(self) -> bool:
        return self.status == "REJECTED"

    @computed_field
    @property
    def is_manually_created(self) -> bool:
        return self.status == "MANUAL"

    @field_validator("bounding_box", "original_bounding_box", mode="after")
    @classmethod
    def normalize_box(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return v
        x = float(v.get("x", v.get("xmin", 0.0)))
        y = float(v.get("y", v.get("ymin", 0.0)))
        width = float(v.get("width", max(0.0, float(v.get("xmax", 0.0)) - x) if "xmax" in v else 0.0))
        height = float(v.get("height", max(0.0, float(v.get("ymax", 0.0)) - y) if "ymax" in v else 0.0))
        xmin = float(v.get("xmin", x))
        ymin = float(v.get("ymin", y))
        xmax = float(v.get("xmax", round(x + width, 6)))
        ymax = float(v.get("ymax", round(y + height, 6)))
        return {
            "x": round(x, 6),
            "y": round(y, 6),
            "width": round(width, 6),
            "height": round(height, 6),
            "xmin": round(xmin, 6),
            "ymin": round(ymin, 6),
            "xmax": round(xmax, 6),
            "ymax": round(ymax, 6),
        }

class ManualObservationCreateRequest(BaseModel):
    """Officer input payload for creating a manual statutory observation."""
    field_type: FieldType
    raw_value: str = Field(..., min_length=1, description="Raw observation text")
    normalized_value: Optional[Dict[str, Any]] = Field(default=None, description="Parsed structured value")
    surface_id: Optional[uuid.UUID] = None
    ocr_region_id: Optional[uuid.UUID] = None
    bounding_box: Optional[BoundingBoxNormalized] = None
    reason: str = Field(..., min_length=3, description="Official reason for manual observation declaration")

class ObservationVerifyRequest(BaseModel):
    """Payload to accept/verify an observation."""
    reason: Optional[str] = Field("Inspector verified", description="Verification comment")

class ObservationCorrectRequest(BaseModel):
    """Payload to correct an observation's raw and/or normalized value."""
    raw_value: Optional[str] = None
    normalized_value: Optional[Dict[str, Any]] = None
    reason: str = Field(..., min_length=3, description="Reason for correcting observation")

class ObservationRejectRequest(BaseModel):
    """Payload to reject an extracted observation."""
    reason: str = Field(..., min_length=3, description="Reason for rejecting observation")

class ObservationStatusUpdateRequest(BaseModel):
    """Payload to update an observation status (e.g., UNCERTAIN, CONFLICTING, UNKNOWN)."""
    status: ObservationStatus
    reason: str = Field(..., min_length=3, description="Justification for status change")

class ConflictGroup(BaseModel):
    """Group of observations for a single statutory field showing conflicts if present."""
    field_type: FieldType
    field_label: str
    has_conflict: bool
    conflict_message: Optional[str] = None
    observations: List[ObservationRead]

class AdjudicationWorkspaceState(BaseModel):
    """Full consolidated workspace state for the adjudication console."""
    inspection_id: uuid.UUID
    inspection_number: str
    surfaces: List[Dict[str, Any]]
    active_surface_id: Optional[uuid.UUID] = None
    ocr_runs: List[Dict[str, Any]]
    regions: List[AdjudicatedOCRRegion]
    observations: List[ObservationRead]
    conflicts: List[ConflictGroup]
    latest_evaluations: List[RuleEvaluationRead]
    evaluation_run_id: Optional[uuid.UUID] = None
    audit_history: List[Dict[str, Any]]

class RuleEvaluationChange(BaseModel):
    """Represents a delta in rule verdict following adjudication re-evaluation."""
    rule_code: str
    statutory_citation: str
    previous_outcome: Optional[RuleOutcome] = None
    new_outcome: RuleOutcome
    legal_rationale: str
    outcome_changed: bool

class RuleReevaluationResponse(BaseModel):
    """Comparison result of deterministic rule engine execution following human adjudication."""
    inspection_id: uuid.UUID
    previous_evaluation_run_id: Optional[uuid.UUID] = None
    new_evaluation_run_id: uuid.UUID
    evaluated_at: datetime
    previous_verdict: Optional[RuleOutcome] = None
    new_verdict: RuleOutcome
    total_rules: int
    pass_count: int
    fail_count: int
    review_count: int
    indeterminate_count: int
    not_applicable_count: int
    changes: List[RuleEvaluationChange]
    evaluations: List[RuleEvaluationRead]
