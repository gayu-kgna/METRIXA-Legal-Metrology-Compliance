import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import RuleOutcome

class RuleEvaluation(Base, TimestampMixin):
    """
    Deterministic Legal Rule Evaluation Result.
    Represents the output of the Rule Engine evaluating a specific RuleDefinition
    against an Inspection's extracted Observations and Evidence.
    AI aids perception; the Rule Engine produces this verifiable legal verdict.
    """
    __tablename__ = "rule_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_definition_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("rule_definitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Verdict (PASS, FAIL, REVIEW, INDETERMINATE, NOT_APPLICABLE)
    outcome: Mapped[RuleOutcome] = mapped_column(SQLEnum(RuleOutcome, name="ruleoutcome", create_type=False), nullable=False, index=True)
    legal_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    statutory_citation: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # Evidence Graph Linkage & Applicability
    evidence_references: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    applicability_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=True, index=True)
    
    # Officer Review & Adjudication Override
    officer_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=True)
    overriding_officer_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    inspection = relationship("Inspection", back_populates="evaluations")
    rule_definition = relationship("RuleDefinition", back_populates="evaluations", lazy="selectin")
    overriding_officer = relationship("User", foreign_keys=[overriding_officer_id], lazy="selectin")

    @property
    def rule_code(self) -> str | None:
        return self.rule_definition.rule_code if self.rule_definition else None
