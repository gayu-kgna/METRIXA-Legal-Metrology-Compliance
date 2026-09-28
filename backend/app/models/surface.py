import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import SurfaceType

class InspectionSurface(Base, TimestampMixin):
    """
    Represents an individual physical surface or captured face of a package.
    Foundation for the multi-surface inspection and 6-surface Digital Twin.
    """
    __tablename__ = "inspection_surfaces"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_type: Mapped[SurfaceType] = mapped_column(SQLEnum(SurfaceType), default=SurfaceType.UNSPECIFIED, nullable=False)
    image_storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    image_width: Mapped[int] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    detected_format: Mapped[str] = mapped_column(String(50), nullable=True)
    quality_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="surfaces")
    ocr_regions = relationship("OCRRegion", back_populates="surface", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="surface")
    evidence_items = relationship("EvidenceItem", back_populates="surface")
