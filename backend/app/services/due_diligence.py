import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.due_diligence import (
    ConfidentialDataStatus,
    DueDiligenceAccessMethod,
    DueDiligenceEvent,
    DueDiligenceEventType,
    FinancialMetric,
    FinancialMetricType,
    ListingDueDiligence,
)
from app.models.listing import Listing
from app.repositories import due_diligence as repository
from app.schemas.due_diligence import (
    DueDiligenceProfileUpdate,
    DueDiligenceSummaryRead,
    FinancialMetricCreate,
    FinancialMetricUpdate,
)

_PROFILE_FIELDS = (
    "access_method",
    "access_status",
    "external_url",
    "broker_contact_name",
    "broker_contact_email",
    "broker_contact_phone",
    "inventory_included",
    "ffe_included",
    "notes",
)

_NONNEGATIVE_METRICS = {
    FinancialMetricType.GROSS_REVENUE,
    FinancialMetricType.INVENTORY_VALUE,
    FinancialMetricType.FFE_VALUE,
}


def listing_exists(db: Session, listing_id: uuid.UUID) -> bool:
    return db.get(Listing, listing_id) is not None


def due_diligence_summary(db: Session, listing_id: uuid.UUID) -> DueDiligenceSummaryRead:
    return DueDiligenceSummaryRead(
        profile=repository.get_profile(db, listing_id),
        metrics=repository.list_metrics(db, listing_id),
    )


def _profile_snapshot(profile: ListingDueDiligence) -> dict[str, object]:
    return jsonable_encoder(
        {
            field_name: getattr(profile, field_name)
            for field_name in _PROFILE_FIELDS
        }
        | {
            "requested_at": profile.requested_at,
            "received_at": profile.received_at,
            "verified_at": profile.verified_at,
        }
    )


def _set_access_timestamps(profile: ListingDueDiligence) -> None:
    now = datetime.now(UTC)
    if profile.access_status in {
        ConfidentialDataStatus.REQUESTED,
        ConfidentialDataStatus.RECEIVED_UNVERIFIED,
        ConfidentialDataStatus.VERIFIED,
    } and profile.requested_at is None:
        profile.requested_at = now
    if profile.access_status in {
        ConfidentialDataStatus.RECEIVED_UNVERIFIED,
        ConfidentialDataStatus.VERIFIED,
    } and profile.received_at is None:
        profile.received_at = now
    if profile.access_status == ConfidentialDataStatus.VERIFIED and profile.verified_at is None:
        profile.verified_at = now


def _validate_profile(profile: ListingDueDiligence) -> None:
    if (
        profile.access_method == DueDiligenceAccessMethod.EXTERNAL_NDA
        and not profile.external_url
    ):
        raise ValueError("External NDA access requires an official external URL")
    if profile.access_method == DueDiligenceAccessMethod.BROKER_CONTACT and not any(
        (
            profile.broker_contact_email,
            profile.broker_contact_phone,
            profile.external_url,
        )
    ):
        raise ValueError("Broker contact access requires email, phone, or an official URL")


def update_profile(
    db: Session,
    listing_id: uuid.UUID,
    update: DueDiligenceProfileUpdate,
    *,
    actor: str,
) -> ListingDueDiligence:
    profile = repository.get_profile(db, listing_id)
    created = profile is None
    if profile is None:
        profile = ListingDueDiligence(
            listing_id=listing_id,
            created_by=actor,
            updated_by=actor,
        )
        db.add(profile)
        db.flush()
        old_value = None
    else:
        old_value = _profile_snapshot(profile)

    for field_name in _PROFILE_FIELDS:
        if field_name not in update.model_fields_set:
            continue
        value = getattr(update, field_name)
        if field_name == "external_url" and value is not None:
            value = str(value)
        setattr(profile, field_name, value)

    profile.updated_by = actor
    _validate_profile(profile)
    _set_access_timestamps(profile)
    new_value = _profile_snapshot(profile)
    db.add(
        DueDiligenceEvent(
            listing_id=listing_id,
            event_type=(
                DueDiligenceEventType.PROFILE_CREATED
                if created
                else DueDiligenceEventType.PROFILE_UPDATED
            ),
            actor=actor,
            old_value=old_value,
            new_value=new_value,
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


def _validate_metric_value(metric_type: FinancialMetricType, amount: Decimal) -> None:
    if metric_type in _NONNEGATIVE_METRICS and amount < 0:
        raise ValueError(f"{metric_type.value} cannot be negative")


def _validate_period(period_start: date | None, period_end: date | None) -> None:
    if period_start is not None and period_end is not None and period_end < period_start:
        raise ValueError("Period end cannot be before period start")


def _metric_snapshot(metric: FinancialMetric) -> dict[str, object]:
    return jsonable_encoder(
        {
            "id": metric.id,
            "metric_type": metric.metric_type,
            "amount": metric.amount,
            "currency": metric.currency,
            "period_start": metric.period_start,
            "period_end": metric.period_end,
            "source": metric.source,
            "source_reference": metric.source_reference,
            "verification_status": metric.verification_status,
            "notes": metric.notes,
        }
    )


def create_metric(
    db: Session,
    listing_id: uuid.UUID,
    create: FinancialMetricCreate,
    *,
    actor: str,
) -> FinancialMetric:
    profile = repository.get_profile(db, listing_id)
    if profile is None or profile.access_status not in {
        ConfidentialDataStatus.RECEIVED_UNVERIFIED,
        ConfidentialDataStatus.VERIFIED,
    }:
        raise ValueError(
            "Financial metrics can be recorded only after confidential data is received"
        )
    _validate_metric_value(create.metric_type, create.amount)
    metric = FinancialMetric(
        listing_id=listing_id,
        created_by=actor,
        updated_by=actor,
        **create.model_dump(),
    )
    db.add(metric)
    db.flush()
    db.add(
        DueDiligenceEvent(
            listing_id=listing_id,
            event_type=DueDiligenceEventType.METRIC_CREATED,
            actor=actor,
            old_value=None,
            new_value=_metric_snapshot(metric),
        )
    )
    db.commit()
    db.refresh(metric)
    return metric


def update_metric(
    db: Session,
    metric: FinancialMetric,
    update: FinancialMetricUpdate,
    *,
    actor: str,
) -> FinancialMetric:
    old_value = _metric_snapshot(metric)
    for field_name in update.model_fields_set:
        setattr(metric, field_name, getattr(update, field_name))
    _validate_metric_value(metric.metric_type, metric.amount)
    _validate_period(metric.period_start, metric.period_end)
    metric.updated_by = actor
    db.add(
        DueDiligenceEvent(
            listing_id=metric.listing_id,
            event_type=DueDiligenceEventType.METRIC_UPDATED,
            actor=actor,
            old_value=old_value,
            new_value=_metric_snapshot(metric),
        )
    )
    db.commit()
    db.refresh(metric)
    return metric


def financial_metric(
    db: Session, listing_id: uuid.UUID, metric_id: uuid.UUID
) -> FinancialMetric | None:
    return repository.get_metric(db, listing_id, metric_id)


def due_diligence_events(db: Session, listing_id: uuid.UUID) -> list[DueDiligenceEvent]:
    return repository.list_events(db, listing_id)
