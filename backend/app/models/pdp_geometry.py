import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import SurfaceType

class PDPGeometry(Base, TimestampMixin):
    """
    Represents Principal Display Panel (PDP) geometric measurements and calibration analysis.
    Preserves strict boundary checks and pixel geometry.
    Physical dimensions are populated ONLY when authentic calibration data exists;
    otherwise physical measurements remain explicitly None/uncalibrated with zero fabrication.
    """
    __tablename__ = "pdp_geometries"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_type: Mapped[SurfaceType] = mapped_column(SQLEnum(SurfaceType, name="surfacetype", create_type=False), nullable=False)


    is_pdp_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_width: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False)

    pdp_bounding_box: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # Normalized {"x", "y", "width", "height"}
    pdp_pixel_width: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pdp_pixel_height: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pdp_pixel_area: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    has_calibration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    calibration_source: Mapped[str] = mapped_column(String(100), nullable=True)
    scale_px_per_mm: Mapped[float] = mapped_column(Float, nullable=True)

    estimated_physical_width_mm: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_physical_height_mm: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_physical_area_sq_cm: Mapped[float] = mapped_column(Float, nullable=True)

    measurement_uncertainty: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    declarations_geometry: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    detection_method: Mapped[str] = mapped_column(String(100), default="CANONICAL_SURFACE_BOUNDS", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)  # COMPLETED, UNCALIBRATED, NOT_PDP_SURFACE, INDETERMINATE

    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    inspection = relationship("Inspection", backref="pdp_geometries")
    surface = relationship("InspectionSurface", backref="pdp_geometries")
