import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

class NormalizedBoundingBox(BaseModel):
    """
    Standard normalized bounding box contract for Metrixa Computer Vision / OCR.
    
    Convention:
    - Origin: Top-Left (0.0, 0.0)
    - Normalized range: [0.0, 1.0] relative to full image width and height
    - x: horizontal offset from left edge (0.0 <= x <= 1.0)
    - y: vertical offset from top edge (0.0 <= y <= 1.0)
    - width: normalized box width (0.0 <= width <= 1.0)
    - height: normalized box height (0.0 <= height <= 1.0)
    """
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized horizontal origin (top-left)")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized vertical origin (top-left)")
    width: float = Field(..., ge=0.0, le=1.0, description="Normalized box width")
    height: float = Field(..., ge=0.0, le=1.0, description="Normalized box height")

    @field_validator("x", "y", "width", "height", mode="before")
    @classmethod
    def validate_finite_numbers(cls, v: Any) -> float:
        import math
        if v is None:
            raise ValueError("Bounding box coordinate cannot be null or undefined")
        try:
            val = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid coordinate value: {v}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Coordinate cannot be NaN or Infinity: {val}")
        if val < 0.0 or val > 1.0:
            raise ValueError(f"Coordinate {val} is outside normalized range [0.0, 1.0]")
        return val

    @field_validator("width")
    @classmethod
    def validate_width_boundary(cls, v: float, info) -> float:
        x_val = info.data.get("x", 0.0)
        if x_val + v > 1.001:  # Allow minimal floating point epsilon
            raise ValueError(f"Bounding box extends beyond right boundary: x ({x_val}) + width ({v}) > 1.0")
        return v

    @field_validator("height")
    @classmethod
    def validate_height_boundary(cls, v: float, info) -> float:
        y_val = info.data.get("y", 0.0)
        if y_val + v > 1.001:
            raise ValueError(f"Bounding box extends beyond bottom boundary: y ({y_val}) + height ({v}) > 1.0")
        return v

    @classmethod
    def from_pixel_coords(
        cls,
        x_px: float,
        y_px: float,
        width_px: float,
        height_px: float,
        img_width: int,
        img_height: int
    ) -> "NormalizedBoundingBox":
        """
        Safely convert pixel coordinates to normalized [0, 1] bounding box,
        clamping coordinates within image boundaries if slight overflow occurs.
        """
        if img_width <= 0 or img_height <= 0:
            raise ValueError(f"Invalid image dimensions: {img_width}x{img_height}")

        norm_x = max(0.0, min(1.0, x_px / img_width))
        norm_y = max(0.0, min(1.0, y_px / img_height))
        norm_w = max(0.0, min(1.0 - norm_x, width_px / img_width))
        norm_h = max(0.0, min(1.0 - norm_y, height_px / img_height))

        return cls(x=round(norm_x, 6), y=round(norm_y, 6), width=round(norm_w, 6), height=round(norm_h, 6))

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

@dataclass
class RawOCRToken:
    """
    A single recognized OCR token or phrase with spatial coordinates and confidence.
    """
    text: str
    confidence: float  # Normalized 0.0 to 1.0
    bounding_box: NormalizedBoundingBox
    polygon_coords: Dict[str, Any] = field(default_factory=dict)
    token_order: int = 0

@dataclass
class OCRRecognitionResult:
    """
    Standard OCR Provider recognition result contract.
    Decouples underlying OCR engine implementation from the Metrixa domain model.
    """
    provider_name: str
    provider_version: Optional[str]
    status: str  # COMPLETED, EMPTY, FAILED, PROVIDER_UNAVAILABLE
    tokens: List[RawOCRToken] = field(default_factory=list)
    raw_text: str = ""
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
