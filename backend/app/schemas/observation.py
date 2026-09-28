import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from app.models.enums import FieldType, ObservationStatus, ObservationSource

class ObservationBase(BaseModel):
    field_type: FieldType
    raw_value: str
    normalized_value: Dict[str, Any] = {}
    source: ObservationSource = ObservationSource.CAMERA_STREAM
    confidence: float = 1.0
    status: ObservationStatus = ObservationStatus.OBSERVED
    bounding_box: Dict[str, Any] = {}
    evidence_reference: Optional[str] = None

    # Measurement Data (non-authoritative until certified)
    package_dimensions: Dict[str, Any] = {}
    pdp_dimensions: Dict[str, Any] = {}
    character_height: Dict[str, Any] = {}
    calibration_info: Dict[str, Any] = {}
    measurement_uncertainty: Dict[str, Any] = {}

class ObservationCreate(ObservationBase):
    inspection_id: uuid.UUID
    ocr_region_id: Optional[uuid.UUID] = None
    surface_id: Optional[uuid.UUID] = None

class ObservationRevise(BaseModel):
    """
    Schema for adjudicating/correcting an observation.
    Requires justification to guarantee historical accountability.
    """
    raw_value: Optional[str] = None
    normalized_value: Optional[Dict[str, Any]] = None
    status: ObservationStatus = ObservationStatus.VERIFIED
    revision_reason: str

class ObservationRead(ObservationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    ocr_region_id: Optional[uuid.UUID] = None
    surface_id: Optional[uuid.UUID] = None
    revision: int
    is_latest: bool
    superseded_by_id: Optional[uuid.UUID] = None
    revision_reason: Optional[str] = None
    observed_at: datetime
    created_at: datetime
