import uuid

from sqlalchemy import Select, or_, select, update
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.tracking import (
    DuplicateReviewStatus,
    ListingEvent,
    ListingSnapshot,
    ListingSourceRecord,
    PossibleDuplicate,
)


def find_source_record(
    db: Session,
    *,
    canonical_url: str,
    source: str,
    external_id: str | None,
) -> ListingSourceRecord | None:
    predicates = [ListingSourceRecord.canonical_url == canonical_url]
    if external_id is not None:
        predicates.append(
            (ListingSourceRecord.source == source)
            & (ListingSourceRecord.external_id == external_id)
        )
    return db.scalar(select(ListingSourceRecord).where(or_(*predicates)))


def find_normalized_address_match(
    db: Session, *, normalized_address: str, city: str
) -> Listing | None:
    return db.scalar(
        select(Listing).where(
            Listing.normalized_address == normalized_address,
            Listing.city.ilike(city),
            Listing.is_duplicate.is_(False),
        )
    )


def city_candidates(db: Session, *, city: str, limit: int = 200) -> list[Listing]:
    statement: Select[tuple[Listing]] = (
        select(Listing)
        .where(Listing.city.ilike(city), Listing.is_duplicate.is_(False))
        .order_by(Listing.last_seen_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_snapshots(db: Session, listing_id: uuid.UUID) -> list[ListingSnapshot]:
    return list(
        db.scalars(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == listing_id)
            .order_by(ListingSnapshot.captured_at.desc(), ListingSnapshot.id.desc())
        )
    )


def list_events(db: Session, listing_id: uuid.UUID) -> list[ListingEvent]:
    return list(
        db.scalars(
            select(ListingEvent)
            .where(ListingEvent.listing_id == listing_id)
            .order_by(ListingEvent.detected_at.desc(), ListingEvent.id.desc())
        )
    )


def list_possible_duplicates(
    db: Session,
    *,
    status: DuplicateReviewStatus | None,
    offset: int,
    limit: int,
) -> list[PossibleDuplicate]:
    statement: Select[tuple[PossibleDuplicate]] = select(PossibleDuplicate)
    if status is not None:
        statement = statement.where(PossibleDuplicate.status == status)
    statement = statement.order_by(PossibleDuplicate.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement))


def get_possible_duplicate(db: Session, review_id: uuid.UUID) -> PossibleDuplicate | None:
    return db.get(PossibleDuplicate, review_id)


def move_tracking_records(
    db: Session, *, source_listing_id: uuid.UUID, target_listing_id: uuid.UUID
) -> None:
    for model in (ListingSourceRecord, ListingSnapshot, ListingEvent):
        db.execute(
            update(model)
            .where(model.listing_id == source_listing_id)
            .values(listing_id=target_listing_id)
        )
