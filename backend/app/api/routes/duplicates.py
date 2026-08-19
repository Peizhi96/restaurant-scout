import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tracking import DuplicateReviewStatus
from app.schemas.tracking import (
    DuplicateResolution,
    PossibleDuplicateRead,
)
from app.services import duplicates as service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[PossibleDuplicateRead])
def list_possible_duplicates(
    db: DbSession,
    review_status: Annotated[
        DuplicateReviewStatus | None, Query(alias="status")
    ] = DuplicateReviewStatus.PENDING,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PossibleDuplicateRead]:
    return service.find_possible_duplicates(
        db, status=review_status, offset=offset, limit=limit
    )


@router.patch("/{review_id}", response_model=PossibleDuplicateRead)
def resolve_possible_duplicate(
    review_id: uuid.UUID, resolution: DuplicateResolution, db: DbSession
) -> PossibleDuplicateRead:
    try:
        review = service.resolve_review(db, review_id, resolution.action)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Possible duplicate review not found",
        )
    return review
