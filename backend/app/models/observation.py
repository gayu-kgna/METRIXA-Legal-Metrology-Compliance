import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum, Text
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import FieldType, ObservationStatus, ObservationSource

class Observation(Base, TimestampMixin):
    """
    Fine-grained statutory observation.
    Maintains complete provenance: links to OCR region, package surface, and inspection.
    Enforces historical preservation: observations cannot be silently overwritten.
    Any correction creates a new revision referencing the prior observation.
    """
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    ocr_region_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_regions.id", ondelete="SET NULL"), nullable=True, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_run_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("entity_parsing_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    
    field_type: Mapped[FieldType] = mapped_column(SQLEnum(FieldType), nullable=False, index=True)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[ObservationSource] = mapped_column(SQLEnum(ObservationSource), default=ObservationSource.CAMERA_STREAM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[ObservationStatus] = mapped_column(SQLEnum(ObservationStatus), default=ObservationStatus.OBSERVED, nullable=False, index=True)
    
    # Evidence & Geometry
    bounding_box: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Measurement Architecture (non-authoritative until adjudicated)
    package_dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {"width_mm", "height_mm", "depth_mm"}
    pdp_dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)      # {"area_sq_cm", "ratio"}
    character_height: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)    # {"height_mm", "method"}
    calibration_info: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)    # {"reference_marker", "scale"}
    measurement_uncertainty: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Immutability & Audit Safeguards (Never silently overwrite historical observations)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    superseded_by_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("observations.id", ondelete="SET NULL"), nullable=True)
    revision_reason: Mapped[str] = mapped_column(Text, nullable=True)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="observations")
    ocr_region = relationship("OCRRegion", back_populates="observations")
    surface = relationship("InspectionSurface", back_populates="observations")
    entity_run = relationship("EntityParsingRun", back_populates="observations")
    superseded_by = relationship("Observation", remote_side=[id], foreign_keys=[superseded_by_id])
