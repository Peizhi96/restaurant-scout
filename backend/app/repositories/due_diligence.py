import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.due_diligence import (
    DueDiligenceEvent,
    FinancialMetric,
    ListingDueDiligence,
)


def get_profile(db: Session, listing_id: uuid.UUID) -> ListingDueDiligence | None:
    return db.scalar(
        select(ListingDueDiligence).where(ListingDueDiligence.listing_id == listing_id)
    )


def list_metrics(db: Session, listing_id: uuid.UUID) -> list[FinancialMetric]:
    statement: Select[tuple[FinancialMetric]] = (
        select(FinancialMetric)
        .where(FinancialMetric.listing_id == listing_id)
        .order_by(
            FinancialMetric.period_end.desc(),
            FinancialMetric.metric_type,
            FinancialMetric.created_at.desc(),
        )
    )
    return list(db.scalars(statement))


def get_metric(
    db: Session, listing_id: uuid.UUID, metric_id: uuid.UUID
) -> FinancialMetric | None:
    return db.scalar(
        select(FinancialMetric).where(
            FinancialMetric.id == metric_id,
            FinancialMetric.listing_id == listing_id,
        )
    )


def list_events(db: Session, listing_id: uuid.UUID) -> list[DueDiligenceEvent]:
    statement: Select[tuple[DueDiligenceEvent]] = (
        select(DueDiligenceEvent)
        .where(DueDiligenceEvent.listing_id == listing_id)
        .order_by(DueDiligenceEvent.created_at.desc(), DueDiligenceEvent.id.desc())
    )
    return list(db.scalars(statement))
