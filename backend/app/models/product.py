import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON
from app.core.database import Base, TimestampMixin, GUID

class Product(Base, TimestampMixin):
    """
    Persistent product entity.
    A product exists independently of individual inspections and accumulates
    historical inspections, label versions, and evolving observations over time.
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    gtin_barcode: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=True)
    brand_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    commodity_type: Mapped[str] = mapped_column(String(100), nullable=True)
    manufacturer_claimed: Mapped[str] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    inspections = relationship("Inspection", back_populates="product", cascade="all, delete-orphan")
    label_versions = relationship("LabelVersion", back_populates="product", cascade="all, delete-orphan")
