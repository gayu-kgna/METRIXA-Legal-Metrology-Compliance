import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, ForeignKey, JSON
from app.core.database import Base, TimestampMixin, GUID

class OCRRegion(Base, TimestampMixin):
    """
    Fine-grained OCR tokens and bounding polygon regions extracted from a surface image.
    Preserves exact spatial coordinates for evidentiary callouts.
    """
    __tablename__ = "ocr_regions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)
    ocr_run_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    raw_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False)  # Normalized {"x": float, "y": float, "width": float, "height": float}
    polygon_coords: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    token_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    surface = relationship("InspectionSurface", back_populates="ocr_regions")
    ocr_run = relationship("OCRRun", back_populates="regions")
    observations = relationship("Observation", back_populates="ocr_region")
