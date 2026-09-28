import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Text
from app.core.database import Base, TimestampMixin, GUID

class EntityParsingRun(Base, TimestampMixin):
    """
    Represents an execution of semantic entity parsing on OCR perception evidence.
    Tracks parser and normalizer versions, metrics, conflicts, and links to generated observations.
    Ensures that re-running parsing never silently destroys historical extraction results.
    """
    __tablename__ = "entity_parsing_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)
    ocr_run_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    parser_version: Mapped[str] = mapped_column(String(50), default="ENTITY-PARSER-v1", nullable=False)
    normalizer_version: Mapped[str] = mapped_column(String(50), default="NORMALIZER-v1", nullable=False)

    total_entities_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_conflicts_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_ambiguities_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)  # COMPLETED, EMPTY, CONFLICTS_DETECTED, FAILED
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", backref="entity_runs")
    surface = relationship("InspectionSurface", backref="entity_runs")
    ocr_run = relationship("OCRRun", backref="entity_runs")
    observations = relationship("Observation", back_populates="entity_run", cascade="all, delete-orphan", lazy="selectin")
