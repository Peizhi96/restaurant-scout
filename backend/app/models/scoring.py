import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ListingScore(Base):
    __tablename__ = "listing_scores"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    corporate_catering_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    restaurant_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), index=True)
    corporate_completeness: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    restaurant_completeness: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    corporate_factors: Mapped[dict[str, Any]] = mapped_column(JSON)
    restaurant_factors: Mapped[dict[str, Any]] = mapped_column(JSON)
    missing_information: Mapped[list[str]] = mapped_column(JSON)
    config_version: Mapped[str] = mapped_column(String(40), default="v1-default")
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listing = relationship("Listing", back_populates="score")
