from pydantic import BaseModel, Field
from typing import Optional

class DossierOptions(BaseModel):
    include_images: bool = True
    include_ocr_dump: bool = True
    max_ocr_tokens: int = 150
    application_version: str = "1.0.0"
    generator_version: str = "1.0.0"

class DossierGenerationResult(BaseModel):
    pdf_bytes: bytes
    sha256_hash: str
    file_size_bytes: int
    generated_at: str
    dossier_id: str
    snapshot_id: str
    inspection_id: str
    report_version: int = 1
