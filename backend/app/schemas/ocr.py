import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

class OCRRunRequest(BaseModel):
    """Request payload to trigger OCR processing on an inspection surface image."""
    preprocessing_variant: Optional[str] = Field(
        default="original",
        description="Preprocessing variant preset: original, grayscale, contrast, clahe, adaptive_threshold, otsu_threshold, deskew_upscale"
    )
    provider_name: Optional[str] = Field(
        default=None,
        description="OCR provider preference: 'tesseract' or 'mock'. Defaults to system configured provider."
    )
    provider: Optional[str] = Field(
        default=None,
        description="Alias for provider_name"
    )

class OCRRegionResponse(BaseModel):
    """Structured OCR region representing an extracted token with normalized coordinates."""
    id: uuid.UUID
    surface_id: uuid.UUID
    ocr_run_id: Optional[uuid.UUID] = None
    raw_text: str
    text: str = ""
    confidence: float
    bounding_box: Dict[str, float] = Field(
        ...,
        description="Normalized bounding box: {'x': float, 'y': float, 'width': float, 'height': float} where origin is top-left and values are in [0, 1]"
    )
    bbox: Dict[str, float] = Field(default_factory=dict)
    polygon_coords: Dict[str, Any] = Field(default_factory=dict)
    token_order: int

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_canonical_region_aliases(self) -> "OCRRegionResponse":
        if not self.text:
            self.text = self.raw_text
        if not self.bbox:
            self.bbox = self.bounding_box
        return self

class OCRRunResponse(BaseModel):
    """Detailed response for an individual OCR execution run."""
    id: uuid.UUID
    ocr_run_id: Optional[uuid.UUID] = None
    inspection_id: uuid.UUID
    surface_id: uuid.UUID
    surface: Optional[Any] = None
    provider_name: str
    provider: Optional[str] = None
    provider_version: Optional[str] = None
    preprocessing_variant: str
    processed_image_ref: Optional[str] = None
    status: str
    total_regions_detected: int
    region_count: int = 0
    total_regions: int = 0
    total_characters_detected: int
    character_count: int = 0
    preprocessing_duration_ms: float
    ocr_duration_ms: float
    total_duration_ms: float
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime
    regions: List[OCRRegionResponse] = Field(default_factory=list)
    run: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_canonical_run_aliases(self) -> "OCRRunResponse":
        if not self.ocr_run_id:
            self.ocr_run_id = self.id
        if not self.provider:
            self.provider = self.provider_name
        if self.surface is not None and not isinstance(self.surface, str):
            if hasattr(self.surface, "surface_type"):
                st = self.surface.surface_type
                self.surface = st.value if hasattr(st, "value") else str(st)
            else:
                self.surface = str(self.surface)
        if self.regions:
            self.region_count = len(self.regions)
        else:
            self.region_count = self.total_regions_detected
        self.total_regions = self.region_count
        self.total_regions_detected = self.region_count
        self.character_count = self.total_characters_detected
        self.duration_ms = round(self.total_duration_ms, 2)
        if self.run is None:
            self.run = {
                "id": str(self.id),
                "surface_id": str(self.surface_id),
                "ocr_provider": self.provider_name,
                "preprocessing_variant": self.preprocessing_variant,
                "raw_text": self.metadata_json.get("raw_text", ""),
                "character_count": self.total_characters_detected,
                "execution_duration_ms": self.total_duration_ms,
                "created_at": self.executed_at.isoformat(),
                "region_count": self.region_count,
                "total_regions": self.region_count,
            }
        return self

class OCRRunListResponse(BaseModel):
    """Historical list of all OCR runs performed on a package surface."""
    surface_id: uuid.UUID
    total_runs: int
    runs: List[OCRRunResponse]
