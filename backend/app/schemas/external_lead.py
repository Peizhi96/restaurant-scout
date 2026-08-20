import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.external_lead import (
    ExternalLeadDiscoveryMethod,
    ExternalLeadSource,
    ExternalLeadStatus,
    ExternalLeadSyncStatus,
)


class ExternalLeadCreate(BaseModel):
    source_url: str = Field(min_length=1, max_length=2000)
    city: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10_000)


class ExternalLeadUpdate(BaseModel):
    city: str | None = Field(default=None, max_length=100)
    status: ExternalLeadStatus | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def require_change(self) -> "ExternalLeadUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Status cannot be null")
        return self


class ExternalLeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: ExternalLeadSource
    source_url: str
    city: str | None
    status: ExternalLeadStatus
    notes: str | None
    discovery_method: ExternalLeadDiscoveryMethod
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class ExternalLeadSyncRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: ExternalLeadSource
    status: ExternalLeadSyncStatus
    messages_scanned: int
    links_found: int
    leads_created: int
    leads_existing: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class BizBuySellEmailSyncStatusRead(BaseModel):
    enabled: bool
    configured: bool
    latest_run: ExternalLeadSyncRunRead | None
