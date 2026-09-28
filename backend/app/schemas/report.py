import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field

class ReportGenerateRequest(BaseModel):
    evaluation_run_id: Optional[uuid.UUID] = None
    evidence_snapshot_id: Optional[uuid.UUID] = None
    include_images: bool = True
    include_ocr_dump: bool = True

class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    evidence_snapshot_id: uuid.UUID
    evaluation_run_id: Optional[uuid.UUID] = None
    report_version: int
    storage_path: str
    sha256_hash: str
    file_size_bytes: int
    status: str
    generated_at: datetime
    generated_by_id: Optional[uuid.UUID] = None
    metadata_json: Dict[str, Any] = {}

    @computed_field
    @property
    def pdf_filename(self) -> str:
        return self.storage_path.split("/")[-1] if self.storage_path else f"dossier_{self.id}.pdf"

class EvidenceSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    evaluation_run_id: Optional[uuid.UUID] = None
    application_version: str
    parser_version: str
    normalizer_version: str
    ocr_provider_version: str
    rule_versions: Dict[str, Any] = {}
    source_record_ids: Dict[str, Any] = {}
    integrity_hash: str
    created_at: datetime
    created_by_id: Optional[uuid.UUID] = None
    metadata_json: Dict[str, Any] = {}

class EvidenceBundleResponse(BaseModel):
    manifest: Dict[str, Any]
    integrity_hash: str
    snapshot_id: Optional[uuid.UUID] = None
    graph: Optional[Dict[str, Any]] = None
