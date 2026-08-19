import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.listing import MarketStatus
from app.models.tracking import DuplicateReviewStatus, EventType, MatchMethod


class ListingSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    source_record_id: uuid.UUID | None
    asking_price: Decimal | None
    monthly_rent: Decimal | None
    description: str | None
    market_status: MarketStatus
    captured_at: datetime


class ListingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    snapshot_id: uuid.UUID | None
    event_type: EventType
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    detected_at: datetime


class PossibleDuplicateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    candidate_listing_id: uuid.UUID
    confidence: float
    match_reasons: dict[str, Any]
    status: DuplicateReviewStatus
    created_at: datetime
    resolved_at: datetime | None


class DuplicateResolutionAction(str, enum.Enum):
    MERGE = "MERGE"
    KEEP_SEPARATE = "KEEP_SEPARATE"


class DuplicateResolution(BaseModel):
    action: DuplicateResolutionAction


class IngestionResultRead(BaseModel):
    listing_id: uuid.UUID
    snapshot_id: uuid.UUID
    event_ids: list[uuid.UUID]
    match_method: MatchMethod
    possible_duplicate_id: uuid.UUID | None
