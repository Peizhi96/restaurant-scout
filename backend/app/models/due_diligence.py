import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DueDiligenceAccessMethod(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    EXTERNAL_NDA = "EXTERNAL_NDA"
    BROKER_CONTACT = "BROKER_CONTACT"


class ConfidentialDataStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    NDA_REQUIRED = "NDA_REQUIRED"
    REQUESTED = "REQUESTED"
    RECEIVED_UNVERIFIED = "RECEIVED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    NOT_PROVIDED = "NOT_PROVIDED"


class FinancialMetricType(str, enum.Enum):
    GROSS_REVENUE = "GROSS_REVENUE"
    CASH_FLOW = "CASH_FLOW"
    SDE = "SDE"
    EBITDA = "EBITDA"
    INVENTORY_VALUE = "INVENTORY_VALUE"
    FFE_VALUE = "FFE_VALUE"


class FinancialVerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"


class DueDiligenceEventType(str, enum.Enum):
    PROFILE_CREATED = "PROFILE_CREATED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    METRIC_CREATED = "METRIC_CREATED"
    METRIC_UPDATED = "METRIC_UPDATED"


class ListingDueDiligence(Base):
    __tablename__ = "listing_due_diligence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    access_method: Mapped[DueDiligenceAccessMethod] = mapped_column(
        Enum(
            DueDiligenceAccessMethod,
            name="due_diligence_access_method",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        default=DueDiligenceAccessMethod.UNKNOWN,
        server_default=DueDiligenceAccessMethod.UNKNOWN.value,
    )
    access_status: Mapped[ConfidentialDataStatus] = mapped_column(
        Enum(
            ConfidentialDataStatus,
            name="confidential_data_status",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        default=ConfidentialDataStatus.UNKNOWN,
        server_default=ConfidentialDataStatus.UNKNOWN.value,
        index=True,
    )
    external_url: Mapped[str | None] = mapped_column(Text)
    broker_contact_name: Mapped[str | None] = mapped_column(String(200))
    broker_contact_email: Mapped[str | None] = mapped_column(String(320))
    broker_contact_phone: Mapped[str | None] = mapped_column(String(50))
    inventory_included: Mapped[bool | None] = mapped_column(Boolean)
    ffe_included: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))
    updated_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    metric_type: Mapped[FinancialMetricType] = mapped_column(
        Enum(
            FinancialMetricType,
            name="financial_metric_type",
            native_enum=False,
            create_constraint=True,
            length=32,
        ),
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(200))
    source_reference: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[FinancialVerificationStatus] = mapped_column(
        Enum(
            FinancialVerificationStatus,
            name="financial_verification_status",
            native_enum=False,
            create_constraint=True,
            length=16,
        ),
        default=FinancialVerificationStatus.UNVERIFIED,
        server_default=FinancialVerificationStatus.UNVERIFIED.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(200))
    updated_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DueDiligenceEvent(Base):
    __tablename__ = "due_diligence_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[DueDiligenceEventType] = mapped_column(
        Enum(
            DueDiligenceEventType,
            name="due_diligence_event_type",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(200))
    old_value: Mapped[dict[str, object] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
