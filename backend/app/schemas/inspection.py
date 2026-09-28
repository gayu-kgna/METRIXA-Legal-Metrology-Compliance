import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from app.models.enums import InspectionOverallStatus
from app.schemas.product import ProductRead
from app.schemas.surface import SurfaceRead
from app.schemas.observation import ObservationRead
from app.schemas.rule import RuleEvaluationRead
from app.schemas.evidence import EvidenceItemRead

class InspectionBase(BaseModel):
    product_id: Optional[uuid.UUID] = None
    retail_outlet_name: Optional[str] = None
    retail_outlet_address: Optional[str] = None
    geo_coordinates: Dict[str, Any] = {}
    notes: Optional[str] = None

class InspectionCreate(InspectionBase):
    inspection_number: Optional[str] = None

class InspectionUpdate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    retail_outlet_name: Optional[str] = None
    retail_outlet_address: Optional[str] = None
    geo_coordinates: Optional[Dict[str, Any]] = None
    overall_status: Optional[InspectionOverallStatus] = None
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

class InspectionRead(InspectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_number: str
    inspector_id: uuid.UUID
    overall_status: InspectionOverallStatus
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class InspectionDetailRead(InspectionRead):
    model_config = ConfigDict(from_attributes=True)

    product: Optional[ProductRead] = None
    surfaces: List[SurfaceRead] = []
    observations: List[ObservationRead] = []
    evaluations: List[RuleEvaluationRead] = []
    evidence_items: List[EvidenceItemRead] = []
