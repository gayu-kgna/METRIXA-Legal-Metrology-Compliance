import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Text
from app.core.database import Base, TimestampMixin, GUID

class OCRRun(Base, TimestampMixin):
    """
    Represents an independent execution of OCR perception on a package surface image.
    Supports multiple runs per image (e.g., varying preprocessing variants, OCR providers),
    ensuring complete historical reproducibility, metrics logging, and auditability.
    """
    __tablename__ = "ocr_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)

    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(50), nullable=True)
    preprocessing_variant: Mapped[str] = mapped_column(String(100), default="original", nullable=False)
    processed_image_ref: Mapped[str] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)  # COMPLETED, EMPTY, FAILED, PROVIDER_UNAVAILABLE
    total_regions_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_characters_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    preprocessing_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ocr_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", backref="ocr_runs")
    surface = relationship("InspectionSurface", backref="ocr_runs")
    regions = relationship("OCRRegion", back_populates="ocr_run", cascade="all, delete-orphan", lazy="selectin")
