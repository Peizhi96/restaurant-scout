import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ListingScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listing_id: uuid.UUID
    corporate_catering_score: Decimal | None
    restaurant_score: Decimal | None
    overall_score: Decimal | None
    corporate_completeness: Decimal
    restaurant_completeness: Decimal
    corporate_factors: dict[str, Any]
    restaurant_factors: dict[str, Any]
    missing_information: list[str]
    config_version: str
    calculated_at: datetime
    updated_at: datetime
