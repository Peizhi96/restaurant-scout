import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.listing import MarketStatus


class EventType(str, enum.Enum):
    NEW_LISTING = "NEW_LISTING"
    PRICE_DROP = "PRICE_DROP"
    PRICE_INCREASE = "PRICE_INCREASE"
    RENT_CHANGE = "RENT_CHANGE"
    STATUS_CHANGE = "STATUS_CHANGE"
    BACK_ON_MARKET = "BACK_ON_MARKET"
    LISTING_REMOVED = "LISTING_REMOVED"


class MatchMethod(str, enum.Enum):
    NEW = "NEW"
    CANONICAL_URL = "CANONICAL_URL"
    NORMALIZED_ADDRESS = "NORMALIZED_ADDRESS"
    FUZZY = "FUZZY"
    REVIEW = "REVIEW"


class DuplicateReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    MERGED = "MERGED"
    DISTINCT = "DISTINCT"


class ListingSourceRecord(Base):
    __tablename__ = "listing_source_records"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    missed_scan_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    market_status: Mapped[MarketStatus] = mapped_column(
        Enum(
            MarketStatus,
            name="source_market_status",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        default=MarketStatus.UNKNOWN,
        server_default=MarketStatus.UNKNOWN.value,
        index=True,
    )


class ListingSnapshot(Base):
    __tablename__ = "listing_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listing_source_records.id", ondelete="SET NULL")
    )
    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    monthly_rent: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    market_status: Mapped[MarketStatus] = mapped_column(
        Enum(
            MarketStatus,
            name="snapshot_market_status",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        default=MarketStatus.UNKNOWN,
        server_default=MarketStatus.UNKNOWN.value,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ListingEvent(Base):
    __tablename__ = "listing_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listing_snapshots.id", ondelete="SET NULL")
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            name="listing_event_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        index=True,
    )
    old_value: Mapped[dict[str, object] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class PossibleDuplicate(Base):
    __tablename__ = "possible_duplicates"
    __table_args__ = (
        UniqueConstraint("listing_id", "candidate_listing_id", name="uq_possible_duplicate_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    candidate_listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float)
    match_reasons: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[DuplicateReviewStatus] = mapped_column(
        Enum(
            DuplicateReviewStatus,
            name="duplicate_review_status",
            native_enum=False,
            create_constraint=True,
            length=16,
        ),
        default=DuplicateReviewStatus.PENDING,
        server_default=DuplicateReviewStatus.PENDING.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
