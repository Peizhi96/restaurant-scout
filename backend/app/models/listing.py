import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ListingStatus(str, enum.Enum):
    NEW = "NEW"
    REVIEWING = "REVIEWING"
    CONTACT_BROKER = "CONTACT_BROKER"
    PASSED = "PASSED"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    REJECTED = "REJECTED"
    SOLD = "SOLD"
    OFF_MARKET = "OFF_MARKET"


class MarketStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SOLD = "SOLD"
    OFF_MARKET = "OFF_MARKET"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    business_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    address: Mapped[str | None] = mapped_column(String(300))
    normalized_address: Mapped[str | None] = mapped_column(String(300), index=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    zip: Mapped[str | None] = mapped_column(String(10))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    monthly_rent: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    size_sqft: Mapped[int | None] = mapped_column(Integer)

    seats: Mapped[int | None] = mapped_column(Integer)
    parking: Mapped[bool | None] = mapped_column(Boolean)
    loading_access: Mapped[bool | None] = mapped_column(Boolean)

    type1_hood: Mapped[bool | None] = mapped_column(Boolean)
    hood_length: Mapped[float | None] = mapped_column(Float)
    grease_trap: Mapped[bool | None] = mapped_column(Boolean)
    walk_in_cooler: Mapped[bool | None] = mapped_column(Boolean)

    source: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text)
    status: Mapped[ListingStatus] = mapped_column(
        Enum(
            ListingStatus,
            name="listing_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        default=ListingStatus.NEW,
        server_default=ListingStatus.NEW.value,
        index=True,
    )
    market_status: Mapped[MarketStatus] = mapped_column(
        Enum(
            MarketStatus,
            name="market_status",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        default=MarketStatus.UNKNOWN,
        server_default=MarketStatus.UNKNOWN.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"), index=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    score = relationship(
        "ListingScore",
        back_populates="listing",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def corporate_catering_score(self) -> Decimal | None:
        return self.score.corporate_catering_score if self.score else None

    @property
    def restaurant_score(self) -> Decimal | None:
        return self.score.restaurant_score if self.score else None

    @property
    def overall_score(self) -> Decimal | None:
        return self.score.overall_score if self.score else None

    @property
    def score_completeness(self) -> Decimal | None:
        if self.score is None:
            return None
        return (
            self.score.corporate_completeness + self.score.restaurant_completeness
        ) / 2
