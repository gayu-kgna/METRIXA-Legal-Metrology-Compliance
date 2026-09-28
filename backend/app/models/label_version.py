import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from app.core.database import Base, TimestampMixin, GUID

class LabelVersion(Base, TimestampMixin):
    """
    Foundation for packaging label versioning.
    Tracks distinct artwork and statutory declaration revisions over the SKU lifecycle.
    """
    __tablename__ = "label_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    canonical_declarations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    visual_layout_hash: Mapped[str] = mapped_column(String(128), nullable=True)
    version_fingerprint: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    source_inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_snapshot_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("evidence_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="label_versions")
    source_inspection = relationship("Inspection", foreign_keys=[source_inspection_id])
    evidence_snapshot = relationship("EvidenceSnapshot", foreign_keys=[evidence_snapshot_id])
