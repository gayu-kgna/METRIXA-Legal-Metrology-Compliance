from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class CalibrationInput(BaseModel):
    """Optional physical calibration parameters."""
    scale_px_per_mm: Optional[float] = Field(None, description="Known physical scale in pixels per millimeter")
    reference_dimension_mm: Optional[float] = Field(None, description="Known physical dimension of a reference marker in mm")
    reference_dimension_px: Optional[float] = Field(None, description="Measured pixel span of the reference marker")
    calibration_source: Optional[str] = Field(default="MANUAL_INPUT", description="Source: MANUAL_INPUT, REFERENCE_MARKER, KNOWN_PACKAGE_DIMENSION")

class DeclarationSpatialPlacement(BaseModel):
    """Spatial position and image-space text geometry of a statutory declaration."""
    field_type: str
    quadrant: str  # TOP_LEFT, TOP_RIGHT, TOP_CENTER, CENTER, BOTTOM_LEFT, BOTTOM_RIGHT, BOTTOM_CENTER
    bounding_box: Dict[str, float]
    estimated_text_height_px: float
    estimated_physical_text_height_mm: Optional[float] = None
    relative_height_to_pdp: float
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
