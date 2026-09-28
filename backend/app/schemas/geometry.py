import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

class PDPGeometryRequest(BaseModel):
    """Optional calibration input for PDP geometry analysis."""
    scale_px_per_mm: Optional[float] = Field(None, description="Known physical scale in pixels per millimeter")
    reference_dimension_mm: Optional[float] = Field(None, description="Known physical dimension of a reference marker in mm")
    reference_dimension_px: Optional[float] = Field(None, description="Measured pixel span of the reference marker")
    calibration_source: Optional[str] = Field(default="MANUAL_INPUT", description="Source of calibration data")

class PDPGeometryResponse(BaseModel):
    """Principal Display Panel geometry and declaration spatial analysis result."""
    id: uuid.UUID
    inspection_id: uuid.UUID
    surface_id: uuid.UUID
    surface_type: str
    is_pdp_candidate: bool
    image_width: int
    image_height: int
    pdp_bounding_box: Dict[str, float]
    pdp_pixel_width: float
    pdp_pixel_height: float
    pdp_pixel_area: float
    pdp_area_px2: float = 0.0
    has_calibration: bool
    is_calibrated: bool = False
    calibration_source: Optional[str] = None
    scale_px_per_mm: Optional[float] = None
    estimated_physical_width_mm: Optional[float] = None
    estimated_physical_height_mm: Optional[float] = None
    estimated_physical_area_sq_cm: Optional[float] = None
    measurement_uncertainty: Dict[str, Any] = Field(default_factory=dict)
    declarations_geometry: Dict[str, Any] = Field(default_factory=dict)
    detection_method: str
    confidence: float
    status: str
    analyzed_at: datetime
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_canonical_aliases(self) -> "PDPGeometryResponse":
        self.pdp_area_px2 = self.pdp_pixel_area
        self.is_calibrated = self.has_calibration
        return self

class PDPGeometryListResponse(BaseModel):
    """Historical list of PDP geometry analyses performed on a surface."""
    surface_id: uuid.UUID
    total_analyses: int
    analyses: List[PDPGeometryResponse]
