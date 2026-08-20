import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_internal_api_key
from app.core.database import get_db
from app.models.listing import ListingStatus
from app.schemas.listing import ListingRead, ListingUpdate
from app.schemas.tracking import ListingEventRead, ListingSnapshotRead
from app.services import listings as service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ListingRead])
def list_listings(
    db: DbSession,
    city: str | None = None,
    status_filter: Annotated[ListingStatus | None, Query(alias="status")] = None,
    type1_hood: bool | None = None,
    min_asking_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_asking_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_monthly_rent: Annotated[Decimal | None, Query(ge=0)] = None,
    min_size_sqft: Annotated[int | None, Query(ge=0)] = None,
    max_size_sqft: Annotated[int | None, Query(ge=0)] = None,
    min_overall_score: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    sort_by: Annotated[str, Query(pattern="^(recent|score)$")] = "recent",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ListingRead]:
    return service.find_listings(
        db,
        city=city,
        status=status_filter,
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


@router.get("/{listing_id}/history", response_model=list[ListingSnapshotRead])
def get_listing_history(listing_id: uuid.UUID, db: DbSession) -> list[ListingSnapshotRead]:
    listing = service.find_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return service.listing_history(db, listing_id)


@router.get("/{listing_id}/events", response_model=list[ListingEventRead])
def get_listing_events(listing_id: uuid.UUID, db: DbSession) -> list[ListingEventRead]:
    listing = service.find_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return service.listing_events(db, listing_id)


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: uuid.UUID, db: DbSession) -> ListingRead:
    listing = service.find_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


@router.patch(
    "/{listing_id}",
    response_model=ListingRead,
    dependencies=[Depends(require_internal_api_key)],
)
def update_listing(listing_id: uuid.UUID, update: ListingUpdate, db: DbSession) -> ListingRead:
    listing = service.find_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return service.apply_listing_update(db, listing, update)
