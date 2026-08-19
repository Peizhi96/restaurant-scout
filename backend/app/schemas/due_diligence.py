import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.due_diligence import (
    ConfidentialDataStatus,
    DueDiligenceAccessMethod,
    DueDiligenceEventType,
    FinancialMetricType,
    FinancialVerificationStatus,
)


class DueDiligenceProfileUpdate(BaseModel):
    access_method: DueDiligenceAccessMethod | None = None
    access_status: ConfidentialDataStatus | None = None
    external_url: HttpUrl | None = None
    broker_contact_name: str | None = Field(default=None, max_length=200)
    broker_contact_email: str | None = Field(default=None, max_length=320)
    broker_contact_phone: str | None = Field(default=None, max_length=50)
    inventory_included: bool | None = None
    ffe_included: bool | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator(
        "broker_contact_name", "broker_contact_email", "broker_contact_phone", mode="before"
    )
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def require_change(self) -> "DueDiligenceProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "access_method" in self.model_fields_set and self.access_method is None:
            raise ValueError("Access method cannot be null")
        if "access_status" in self.model_fields_set and self.access_status is None:
            raise ValueError("Access status cannot be null")
        return self


class DueDiligenceProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    access_method: DueDiligenceAccessMethod
    access_status: ConfidentialDataStatus
    external_url: str | None
    broker_contact_name: str | None
    broker_contact_email: str | None
    broker_contact_phone: str | None
    inventory_included: bool | None
    ffe_included: bool | None
    notes: str | None
    requested_at: datetime | None
    received_at: datetime | None
    verified_at: datetime | None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class FinancialMetricBase(BaseModel):
    metric_type: FinancialMetricType
    amount: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)
    period_start: date | None = None
    period_end: date | None = None
    source: str = Field(min_length=1, max_length=200)
    source_reference: str | None = None
    verification_status: FinancialVerificationStatus = FinancialVerificationStatus.UNVERIFIED
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_period(self) -> "FinancialMetricBase":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("Period end cannot be before period start")
        return self


class FinancialMetricCreate(FinancialMetricBase):
    pass


class FinancialMetricUpdate(BaseModel):
    metric_type: FinancialMetricType | None = None
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    period_start: date | None = None
    period_end: date | None = None
    source: str | None = Field(default=None, max_length=200)
    source_reference: str | None = None
    verification_status: FinancialVerificationStatus | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def require_change(self) -> "FinancialMetricUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        required_fields = {
            "metric_type",
            "amount",
            "currency",
            "source",
            "verification_status",
        }
        if any(
            name in self.model_fields_set and getattr(self, name) is None
            for name in required_fields
        ):
            raise ValueError("Required financial metric fields cannot be null")
        if "source" in self.model_fields_set and not self.source:
            raise ValueError("Source cannot be empty")
        return self


class FinancialMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    metric_type: FinancialMetricType
    amount: Decimal
    currency: str
    period_start: date | None
    period_end: date | None
    source: str
    source_reference: str | None
    verification_status: FinancialVerificationStatus
    notes: str | None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class DueDiligenceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    event_type: DueDiligenceEventType
    actor: str
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    created_at: datetime


class DueDiligenceSummaryRead(BaseModel):
    profile: DueDiligenceProfileRead | None
    metrics: list[FinancialMetricRead]
