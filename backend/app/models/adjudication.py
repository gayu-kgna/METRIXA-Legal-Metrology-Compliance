import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import CorrectionType

class OCRAdjudication(Base, TimestampMixin):
    """
    Dedicated immutable OCR Region Adjudication & Correction Record.
    Preserves historical OCR integrity: original OCR runs and regions remain unchanged.
    Tracks human corrections, revisions, manual additions, and region rejections.
    """
    __tablename__ = "ocr_adjudications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)
    ocr_run_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    ocr_region_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_regions.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_adjudication_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("ocr_adjudications.id", ondelete="SET NULL"), nullable=True)

    correction_type: Mapped[CorrectionType] = mapped_column(SQLEnum(CorrectionType, name="correctiontype", create_type=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="CORRECTED", nullable=False, index=True)  # ORIGINAL, CORRECTED, MANUAL, REJECTED

    original_text: Mapped[str] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=True)

    original_bounding_box: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    corrected_bounding_box: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    original_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    adjudicated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", backref="adjudications")
    surface = relationship("InspectionSurface", backref="adjudications")
    ocr_run = relationship("OCRRun", backref="adjudications")
    ocr_region = relationship("OCRRegion", backref="adjudications")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    parent_adjudication = relationship("OCRAdjudication", remote_side=[id], foreign_keys=[parent_adjudication_id])
