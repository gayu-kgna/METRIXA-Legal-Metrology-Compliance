import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Text
from app.core.database import Base, TimestampMixin, GUID

class InspectionReport(Base, TimestampMixin):
    """
    Generated Inspection Dossier Report record.
    Tracks each generated explainable PDF dossier, its sequential version number,
    linkage to the immutable EvidenceSnapshot, logical storage path, and cryptographic SHA-256 seal.
    Never overwrites previous historical reports.
    """
    __tablename__ = "inspection_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_snapshot_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("evidence_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=True, index=True)

    report_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="GENERATED", nullable=False)  # GENERATED, ARCHIVED
    generated_by_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="reports")
    evidence_snapshot = relationship("EvidenceSnapshot", back_populates="reports", lazy="selectin")
    generated_by = relationship("User", foreign_keys=[generated_by_id], lazy="selectin")
