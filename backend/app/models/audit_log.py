import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from app.core.database import Base, GUID

class AuditLog(Base):
    """
    Immutable Audit Log.
    Tracks all enforcement actions, manual overrides, observation corrections,
    and evidence sealing events for legal accountability and chain of custody.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # e.g., "OBSERVATION_ADJUDICATED", "RULE_OVERRIDDEN"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)          # e.g., "Observation", "RuleEvaluation"
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    previous_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    new_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
