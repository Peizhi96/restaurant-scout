import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExternalLeadSource(str, enum.Enum):
    BIZBUYSELL = "BIZBUYSELL"
    LOOPNET = "LOOPNET"


class ExternalLeadStatus(str, enum.Enum):
    NEW = "NEW"
    REVIEWING = "REVIEWING"
    CONTACT_BROKER = "CONTACT_BROKER"
    PASSED = "PASSED"


class ExternalLead(Base):
    __tablename__ = "external_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[ExternalLeadSource] = mapped_column(
        Enum(
            ExternalLeadSource,
            name="external_lead_source",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        index=True,
    )
    source_url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[ExternalLeadStatus] = mapped_column(
        Enum(
            ExternalLeadStatus,
            name="external_lead_status",
            native_enum=False,
            create_constraint=True,
            length=24,
        ),
        default=ExternalLeadStatus.NEW,
        server_default=ExternalLeadStatus.NEW.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
