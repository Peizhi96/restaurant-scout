import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.listing import ListingStatus, MarketStatus


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    business_name: str | None
    description: str | None
    address: str | None
    normalized_address: str | None
    city: str
    zip: str | None
    lat: float | None
    lng: float | None
    asking_price: Decimal | None
    monthly_rent: Decimal | None
    size_sqft: int | None
    seats: int | None
    parking: bool | None
    loading_access: bool | None
    type1_hood: bool | None
    hood_length: float | None
    grease_trap: bool | None
    walk_in_cooler: bool | None
    source: str
    source_url: str
    status: ListingStatus
    market_status: MarketStatus
    notes: str | None
    is_duplicate: bool
    merged_into_id: uuid.UUID | None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class ListingUpdate(BaseModel):
    status: ListingStatus | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def require_change(self) -> "ListingUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Status cannot be null")
        return self


class ListingObservation(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    business_name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    address: str | None = Field(default=None, max_length=300)
    city: str = Field(min_length=1, max_length=100)
    zip: str | None = Field(default=None, max_length=10)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    asking_price: Decimal | None = Field(default=None, ge=0)
    monthly_rent: Decimal | None = Field(default=None, ge=0)
    size_sqft: int | None = Field(default=None, ge=0)
    seats: int | None = Field(default=None, ge=0)
    parking: bool | None = None
    loading_access: bool | None = None
    type1_hood: bool | None = None
    hood_length: float | None = Field(default=None, ge=0)
    grease_trap: bool | None = None
    walk_in_cooler: bool | None = None
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1)
    external_id: str | None = Field(default=None, max_length=255)
    market_status: MarketStatus = MarketStatus.UNKNOWN
    captured_at: datetime
    raw_payload: dict[str, Any] = Field(default_factory=dict)
