import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from app.models.enums import FieldType, ObservationStatus

PARSER_VERSION = "ENTITY-PARSER-v1"
NORMALIZER_VERSION = "NORMALIZER-v1"

class QuantityNormalized(BaseModel):
    value: float = Field(..., description="Observed numeric quantity value")
    unit: str = Field(..., description="Normalized unit (e.g., g, ml, pcs)")
    raw_unit: str = Field(..., description="Original raw unit string from label")
    raw_declaration: Optional[str] = Field(None, description="Original raw declaration string from label")
    base_quantity: float = Field(..., description="Normalized quantity in base unit (e.g., g for mass, ml for volume)")
    base_unit: str = Field(..., description="Canonical base unit (g, ml, units)")
    count: Optional[int] = Field(None, description="Package count for multi-packs (e.g., 10 in '10 packs of 71g')")
    individual_quantity: Optional[float] = Field(None, description="Individual unit quantity in multi-packs (e.g. 71.0)")
    individual_unit: Optional[str] = Field(None, description="Individual unit in multi-packs (e.g. 'g')")
    total_quantity: Optional[float] = Field(None, description="Total derived quantity across all items (e.g. 710.0)")
    total_unit: Optional[str] = Field(None, description="Total unit across all items (e.g. 'g')")

class MRPNormalized(BaseModel):
    value: float = Field(..., description="Numeric maximum retail price")
    currency: str = Field(default="INR", description="Currency code")
    currency_symbol: Optional[str] = Field(default="₹", description="Observed currency symbol (₹, Rs, INR)")
    raw_amount: str = Field(..., description="Exact OCR snippet of amount")
    includes_taxes: bool = Field(default=True, description="Whether inclusive of all taxes wording is indicated")

class DateNormalized(BaseModel):
    date_iso: Optional[str] = Field(None, description="ISO-8601 formatted date (e.g. '2026-01-01' or '2026-01')")
    date_type: str = Field(..., description="MFG, PKD, IMPORT, BEST_BEFORE, USE_BY, EXPIRY")
    precision: str = Field(..., description="DAY_MONTH_YEAR, MONTH_YEAR, YEAR")
    day: Optional[int] = None
    month: Optional[int] = None
    year: int
    is_ambiguous: bool = Field(default=False, description="True if format cannot distinguish day vs month (e.g. 03/04/2026)")
    ambiguity_reason: Optional[str] = None

class ConsumerCareNormalized(BaseModel):
    phones: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    addresses: List[str] = Field(default_factory=list)
    website: Optional[str] = None

class PartyNormalized(BaseModel):
    entity_type: str = Field(..., description="MANUFACTURER, PACKER, IMPORTER, MARKETED_BY, MARKETER")
    name: str = Field(..., description="Identified legal name of entity")
    address: Optional[str] = Field(None, description="Identified address of entity")

class CountryOfOriginNormalized(BaseModel):
    country: str = Field(..., description="Country name")
    raw_statement: str = Field(..., description="Original declaration phrase observed")

class UnitSalePriceNormalized(BaseModel):
    value: float = Field(..., description="Unit sale price value")
    currency: str = Field(default="INR")
    unit: str = Field(..., description="Unit denominator (e.g., kg, g, l, 100 g)")

@dataclass
class ParsedEntity:
    """
    High-fidelity semantic entity extracted from OCR perception evidence.
    Retains explicit separation of raw OCR text from structured normalized value,
    and records precise bounding polygon and contributing OCR region IDs.
    """
    field_type: FieldType
    raw_value: str
    normalized_value: Dict[str, Any]
    status: ObservationStatus
    confidence: float
    bounding_box: Dict[str, float]  # Normalized {"x", "y", "width", "height"}
    source_region_ids: List[uuid.UUID] = field(default_factory=list)
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    is_conflicting: bool = False
    conflict_details: Optional[Dict[str, Any]] = None
    parser_version: str = PARSER_VERSION
    normalizer_version: str = NORMALIZER_VERSION
