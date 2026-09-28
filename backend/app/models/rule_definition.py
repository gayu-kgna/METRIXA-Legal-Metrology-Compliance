import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, JSON, Text, Enum as SQLEnum, UniqueConstraint
from app.core.database import Base, TimestampMixin, GUID
from app.models.enums import RuleSeverity

class RuleDefinition(Base, TimestampMixin):
    """
    Versioned Legal Metrology Rule Definition.
    Fully declarative representation of statutory provisions under
    Legal Metrology Act, 2009 and Legal Metrology (Packaged Commodities) Rules, 2011.
    Supports versioning, applicability conditions, exemptions, and amendment tracking.
    """
    __tablename__ = "rule_definitions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    rule_code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    legal_act: Mapped[str] = mapped_column(String(255), default="Legal Metrology Act, 2009", nullable=False)
    rule_reference: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Rule 6(1)(e)"
    clause_reference: Mapped[str] = mapped_column(String(255), nullable=True)  # e.g., "Sub-rule (1) Clause (e)"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Official Citations & Source Documentation
    source_document: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "G.S.R. 202(E) dated 7th March 2011"
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Temporal Validity & Amendments
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Declarative Evaluation Logic & Conditions (No hardcoding)
    applicability_conditions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    exemptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evaluation_logic: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    severity: Mapped[RuleSeverity] = mapped_column(SQLEnum(RuleSeverity), default=RuleSeverity.MANDATORY, nullable=False)
    evidence_requirements: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), default="IN", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="MANDATORY_DECLARATION", nullable=False, index=True)
    is_test_rule: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    evaluations = relationship("RuleEvaluation", back_populates="rule_definition", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("rule_code", "version", name="uq_rule_code_version"),
    )
