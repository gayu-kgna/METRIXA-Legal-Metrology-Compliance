import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class EvidenceItemBase(BaseModel):
    evidence_type: str  # CROPPED_REGION, HASH_SEAL, METRIC_PROOF
    bounding_box: Dict[str, Any] = {}
    cropped_storage_path: Optional[str] = None
    sha256_hash: str
    tamper_seal_metadata: Dict[str, Any] = {}
    notes: Optional[str] = None

class EvidenceItemCreate(EvidenceItemBase):
    inspection_id: uuid.UUID
    surface_id: uuid.UUID

class EvidenceItemRead(EvidenceItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    surface_id: uuid.UUID
    created_at: datetime

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    justification: str
    ip_address: Optional[str] = None
    performed_at: datetime
