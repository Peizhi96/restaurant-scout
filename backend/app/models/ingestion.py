import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CollectionRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RawListingStatus(str, enum.Enum):
    COLLECTED = "COLLECTED"
    INGESTED = "INGESTED"
    FAILED = "FAILED"


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collector_name: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[CollectionRunStatus] = mapped_column(
        Enum(
            CollectionRunStatus,
            name="collection_run_status",
            native_enum=False,
            create_constraint=True,
            length=16,
        ),
        default=CollectionRunStatus.RUNNING,
        server_default=CollectionRunStatus.RUNNING.value,
        index=True,
    )
    collected_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    succeeded_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reconciled_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source_removed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    listing_removed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RawListingRecord(Base):
    __tablename__ = "raw_listings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("collection_runs.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(100), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[RawListingStatus] = mapped_column(
        Enum(
            RawListingStatus,
            name="raw_listing_status",
            native_enum=False,
            create_constraint=True,
            length=16,
        ),
        default=RawListingStatus.COLLECTED,
        server_default=RawListingStatus.COLLECTED.value,
        index=True,
    )
    normalized_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"), index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
