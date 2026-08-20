import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.ingestion import CollectionRunStatus, RawListingStatus


class RawListing(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1)
    external_id: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any]
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ManualListingInput(BaseModel):
    source_url: str = Field(min_length=1)
    external_id: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any]
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ManualIngestionRequest(BaseModel):
    items: list[ManualListingInput] = Field(min_length=1, max_length=500)


class AutomatedCollectorName(str, Enum):
    RESTAURANT_REALTY = "restaurant_realty"
    RESTAURANT_FOR_SALES = "restaurant_for_sales"
    BIZBUYSELL = "bizbuysell"
    LOOPNET = "loopnet"


class AutomatedScanRequest(BaseModel):
    collector: AutomatedCollectorName


class CollectionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collector_name: str
    status: CollectionRunStatus
    collected_count: int
    succeeded_count: int
    failed_count: int
    reconciled_count: int
    source_removed_count: int
    listing_removed_count: int
    error_summary: str | None
    started_at: datetime
    completed_at: datetime | None


class RawListingRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    source: str
    external_id: str | None
    source_url: str
    payload: dict[str, Any]
    collected_at: datetime
    status: RawListingStatus
    normalized_payload: dict[str, Any] | None
    listing_id: uuid.UUID | None
    error_message: str | None
    created_at: datetime
    processed_at: datetime | None
