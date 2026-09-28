import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, JSON, Text
from app.core.database import Base, TimestampMixin, GUID

class EvidenceItem(Base, TimestampMixin):
    """
    Evidence item for an inspection.
    Forms part of the tamper-evident evidence package.
    Can represent an on-demand cropped image region, cryptographic hash seal,
    or visual callout linking directly back to original package imagery.
    """
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    surface_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspection_surfaces.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CROPPED_REGION, HASH_SEAL, METRIC_PROOF
    bounding_box: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cropped_storage_path: Mapped[str] = mapped_column(String(500), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tamper_seal_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    inspection = relationship("Inspection", back_populates="evidence_items")
    surface = relationship("InspectionSurface", back_populates="evidence_items")


class EvidenceSnapshot(Base, TimestampMixin):
    """
    Immutable Evidence Snapshot.
    Captures the exact point-in-time perception and evaluation state of an inspection,
    including the active OCR runs, entity parsing runs, observations, PDP geometry,
    and rule evaluation runs used to produce a dossier.
    Immutable: never overwritten when subsequent runs take place.
    """
    __tablename__ = "evidence_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=True, index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    application_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), default="ENTITY-PARSER-v1", nullable=False)
    normalizer_version: Mapped[str] = mapped_column(String(50), default="NORMALIZER-v1", nullable=False)
    ocr_provider_version: Mapped[str] = mapped_column(String(100), default="Modular OCR Engine", nullable=False)
    rule_versions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    source_record_ids: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="evidence_snapshots")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    reports = relationship("InspectionReport", back_populates="evidence_snapshot", cascade="all, delete-orphan")
