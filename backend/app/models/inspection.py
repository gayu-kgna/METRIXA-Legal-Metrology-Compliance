import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import InspectionOverallStatus

class Inspection(Base, TimestampMixin):
    """
    Point-in-time Legal Metrology Inspection Event.
    Separated from the Product entity. A product can have many inspections over its lifetime.
    Maintains all surfaces, observations, evaluations, evidence items, and audit entries.
    """
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    label_version_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("label_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    inspector_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Inspection Site Context
    retail_outlet_name: Mapped[str] = mapped_column(String(255), nullable=True)
    retail_outlet_address: Mapped[str] = mapped_column(Text, nullable=True)
    geo_coordinates: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {"lat": float, "lng": float, "accuracy_m": float}
    
    # Overall Assessment
    overall_status: Mapped[InspectionOverallStatus] = mapped_column(
        SQLEnum(InspectionOverallStatus),
        default=InspectionOverallStatus.PENDING,
        nullable=False,
        index=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamps
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    product = relationship("Product", back_populates="inspections")
    label_version = relationship("LabelVersion", foreign_keys=[label_version_id])
    inspector = relationship("User", back_populates="inspections", foreign_keys=[inspector_id])
    surfaces = relationship("InspectionSurface", back_populates="inspection", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="inspection", cascade="all, delete-orphan")
    evaluations = relationship("RuleEvaluation", back_populates="inspection", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="inspection", cascade="all, delete-orphan")
    evidence_snapshots = relationship("EvidenceSnapshot", back_populates="inspection", cascade="all, delete-orphan")
    reports = relationship("InspectionReport", back_populates="inspection", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="inspection", cascade="all, delete-orphan")
