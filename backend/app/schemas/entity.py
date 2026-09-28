import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.schemas.observation import ObservationRead

class EntityParseRequest(BaseModel):
    """Request payload to trigger semantic entity parsing on OCR perception evidence."""
    ocr_run_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional OCR run ID. Defaults to latest completed OCR run for the surface."
    )

class EntityRunResponse(BaseModel):
    """Execution details and generated observations from an entity parsing run."""
    id: uuid.UUID
    inspection_id: uuid.UUID
    surface_id: uuid.UUID
    ocr_run_id: uuid.UUID
    parser_version: str
    normalizer_version: str
    total_entities_extracted: int
    entity_count: int = 0
    total_conflicts_detected: int
    conflict_count: int = 0
    total_ambiguities_detected: int
    ambiguity_count: int = 0
    status: str
    duration_ms: float
    error_message: Optional[str] = None
    executed_at: datetime
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    observations: List[ObservationRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_canonical_aliases(self) -> "EntityRunResponse":
        self.entity_count = self.total_entities_extracted
        self.conflict_count = self.total_conflicts_detected
        self.ambiguity_count = self.total_ambiguities_detected
        return self

class EntityRunListResponse(BaseModel):
    """Historical list of all entity parsing runs on a package surface."""
    surface_id: uuid.UUID
    total_runs: int
    runs: List[EntityRunResponse]
