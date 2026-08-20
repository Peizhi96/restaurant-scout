import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.intelligence import AIRecommendation


class AIAnalysisOutput(BaseModel):
    recommendation: AIRecommendation
    strengths: list[str] = Field(max_length=6)
    risks: list[str] = Field(max_length=6)
    missing_information: list[str] = Field(max_length=12)
    confidence: Decimal = Field(ge=0, le=1)

    @field_validator("strengths", "risks", "missing_information")
    @classmethod
    def clean_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip()[:500] for item in value if item.strip()]
        return list(dict.fromkeys(cleaned))


class ListingAIAnalysisRead(AIAnalysisOutput):
    model_config = ConfigDict(from_attributes=True)

    listing_id: uuid.UUID
    model: str
    prompt_version: str
    generated_at: datetime
    updated_at: datetime


class AIAnalysisGenerateRequest(BaseModel):
    force: bool = False
