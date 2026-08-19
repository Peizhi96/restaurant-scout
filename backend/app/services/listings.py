import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.listing import Listing, ListingStatus
from app.models.tracking import ListingEvent, ListingSnapshot
from app.repositories import listings as repository
from app.repositories import tracking as tracking_repository
from app.schemas.listing import ListingUpdate


def find_listings(
    db: Session,
    *,
    city: str | None,
    status: ListingStatus | None,
    type1_hood: bool | None,
    min_asking_price: Decimal | None,
    max_asking_price: Decimal | None,
    max_monthly_rent: Decimal | None,
    min_size_sqft: int | None,
    max_size_sqft: int | None,
    min_overall_score: Decimal | None,
    sort_by: str,
    offset: int,
    limit: int,
) -> list[Listing]:
    return repository.list_listings(
        db,
        city=city,
        status=status,
        type1_hood=type1_hood,
        min_asking_price=min_asking_price,
        max_asking_price=max_asking_price,
        max_monthly_rent=max_monthly_rent,
        min_size_sqft=min_size_sqft,
        max_size_sqft=max_size_sqft,
        min_overall_score=min_overall_score,
        sort_by=sort_by,
        offset=offset,
        limit=limit,
    )


def find_listing(db: Session, listing_id: uuid.UUID) -> Listing | None:
    return repository.get_listing(db, listing_id)


def apply_listing_update(db: Session, listing: Listing, update: ListingUpdate) -> Listing:
    return repository.update_listing(
        db,
        listing,
        status=update.status,
        notes=update.notes,
        fields_set=update.model_fields_set,
    )


def listing_history(db: Session, listing_id: uuid.UUID) -> list[ListingSnapshot]:
    return tracking_repository.list_snapshots(db, listing_id)


def listing_events(db: Session, listing_id: uuid.UUID) -> list[ListingEvent]:
    return tracking_repository.list_events(db, listing_id)
