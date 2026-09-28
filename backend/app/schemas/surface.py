import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from app.models.enums import SurfaceType

class SurfaceBase(BaseModel):
    surface_type: SurfaceType = SurfaceType.UNSPECIFIED
    image_storage_path: str
    sha256_hash: str
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    detected_format: Optional[str] = None
    quality_metrics: Dict[str, Any] = {}

class SurfaceCreate(SurfaceBase):
    inspection_id: uuid.UUID

class SurfaceRead(SurfaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    captured_at: datetime
    created_at: datetime

class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    surface_type: SurfaceType
    original_filename: Optional[str] = None
    mime_type: str
    detected_format: str
    file_size_bytes: int
    image_width: int
    image_height: int
    sha256_hash: str
    storage_reference: str
    is_duplicate: bool = False
    duplicate_of_surface_id: Optional[uuid.UUID] = None
    captured_at: datetime
    quality_metrics: Dict[str, Any] = {}

class OCRRegionBase(BaseModel):
    raw_text: str
    confidence: float = 1.0
    bounding_box: Dict[str, float]  # {"ymin": float, "xmin": float, "ymax": float, "xmax": float}
    polygon_coords: Dict[str, Any] = {}
    token_order: int = 0

class OCRRegionCreate(OCRRegionBase):
    surface_id: uuid.UUID

class OCRRegionRead(OCRRegionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    surface_id: uuid.UUID
    created_at: datetime
