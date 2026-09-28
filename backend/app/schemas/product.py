import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List

class ProductBase(BaseModel):
    gtin_barcode: Optional[str] = None
    brand_name: str
    product_name: str
    category: Optional[str] = None
    commodity_type: Optional[str] = None
    manufacturer_claimed: Optional[str] = None
    metadata_json: Dict[str, Any] = {}

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    gtin_barcode: Optional[str] = None
    brand_name: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    commodity_type: Optional[str] = None
    manufacturer_claimed: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

# Phase 9: Product Ledger Schemas

class ProductLedgerItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gtin_barcode: Optional[str] = None
    brand_name: str
    product_name: str
    category: Optional[str] = None
    commodity_type: Optional[str] = None
    manufacturer_claimed: Optional[str] = None
    inspection_count: int = 0
    latest_inspection_date: Optional[datetime] = None
    latest_label_version: Optional[str] = None
    latest_status: Optional[str] = None
    created_at: datetime

class ProductDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gtin_barcode: Optional[str] = None
    brand_name: str
    product_name: str
    category: Optional[str] = None
    commodity_type: Optional[str] = None
    manufacturer_claimed: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    known_declarations: Dict[str, Any] = {}
    inspection_count: int = 0
    first_inspection_date: Optional[datetime] = None
    latest_inspection_date: Optional[datetime] = None
    latest_status: Optional[str] = None
    latest_label_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class LabelVersionBase(BaseModel):
    version_tag: str = "v1.0"
    canonical_declarations: Dict[str, Any] = {}
    visual_layout_hash: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    notes: Optional[str] = None

class LabelVersionCreate(LabelVersionBase):
    product_id: Optional[uuid.UUID] = None
    source_inspection_id: Optional[uuid.UUID] = None
    evidence_snapshot_id: Optional[uuid.UUID] = None
    version_fingerprint: Optional[str] = None
    metadata_json: Dict[str, Any] = {}

class LabelVersionRead(LabelVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    version_fingerprint: Optional[str] = None
    source_inspection_id: Optional[uuid.UUID] = None
    evidence_snapshot_id: Optional[uuid.UUID] = None
    created_at: datetime

class LabelVersionDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    version_tag: str
    version_fingerprint: Optional[str] = None
    canonical_declarations: Dict[str, Any] = {}
    source_inspection_id: Optional[uuid.UUID] = None
    source_inspection_number: Optional[str] = None
    evidence_snapshot_id: Optional[uuid.UUID] = None
    report_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: datetime

class FieldComparisonItem(BaseModel):
    field: str
    field_label: str
    prev_value: Optional[Any] = None
    curr_value: Optional[Any] = None
    prev_source: Optional[str] = None
    curr_source: Optional[str] = None

class LabelDiffResponse(BaseModel):
    from_version_id: uuid.UUID
    from_version_tag: str
    to_version_id: uuid.UUID
    to_version_tag: str
    changed_fields: List[FieldComparisonItem] = []
    added_fields: List[FieldComparisonItem] = []
    removed_fields: List[FieldComparisonItem] = []
    unchanged_fields: List[FieldComparisonItem] = []
    total_changes: int = 0
    legal_disclaimer: str = (
        "A changed value is a factual historical difference between packaging revisions. "
        "The deterministic rule engine remains the sole authority for legal compliance evaluations."
    )

class TimelineEventRead(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    title: str
    description: str
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    badge_number: Optional[str] = None
    inspection_id: Optional[uuid.UUID] = None
    inspection_number: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ProductInspectionItemRead(BaseModel):
    id: uuid.UUID
    inspection_number: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    retail_outlet_name: Optional[str] = None
    retail_outlet_address: Optional[str] = None
    inspector_name: Optional[str] = None
    inspector_badge: Optional[str] = None
    overall_status: str
    label_version_tag: Optional[str] = None
    rule_verdict: Optional[str] = None
    has_report: bool = False
    report_id: Optional[uuid.UUID] = None
    report_pdf_path: Optional[str] = None
