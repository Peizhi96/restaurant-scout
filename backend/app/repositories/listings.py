import uuid
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.listing import Listing, ListingStatus


def get_listing(db: Session, listing_id: uuid.UUID) -> Listing | None:
    return db.get(Listing, listing_id)


def list_listings(
    db: Session,
    *,
    city: str | None = None,
    status: ListingStatus | None = None,
    type1_hood: bool | None = None,
    min_asking_price: Decimal | None = None,
    max_asking_price: Decimal | None = None,
    max_monthly_rent: Decimal | None = None,
    min_size_sqft: int | None = None,
    max_size_sqft: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Listing]:
    statement: Select[tuple[Listing]] = select(Listing).where(Listing.is_duplicate.is_(False))

    if city is not None:
        statement = statement.where(Listing.city.ilike(city.strip()))
    if status is not None:
        statement = statement.where(Listing.status == status)
    if type1_hood is not None:
        statement = statement.where(Listing.type1_hood == type1_hood)
    if min_asking_price is not None:
        statement = statement.where(Listing.asking_price >= min_asking_price)
    if max_asking_price is not None:
        statement = statement.where(Listing.asking_price <= max_asking_price)
    if max_monthly_rent is not None:
        statement = statement.where(Listing.monthly_rent <= max_monthly_rent)
    if min_size_sqft is not None:
        statement = statement.where(Listing.size_sqft >= min_size_sqft)
    if max_size_sqft is not None:
        statement = statement.where(Listing.size_sqft <= max_size_sqft)

    statement = (
        statement.order_by(Listing.last_seen_at.desc(), Listing.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def update_listing(
    db: Session,
    listing: Listing,
    *,
    status: ListingStatus | None,
    notes: str | None,
    fields_set: set[str],
) -> Listing:
    if "status" in fields_set and status is not None:
        listing.status = status
    if "notes" in fields_set:
        listing.notes = notes
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing
