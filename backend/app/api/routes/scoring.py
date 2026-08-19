import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.scoring import ListingScoreRead
from app.services import scoring as service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{listing_id}/scores", response_model=ListingScoreRead)
def get_listing_scores(listing_id: uuid.UUID, db: DbSession) -> ListingScoreRead:
    score = service.get_or_calculate_score(db, listing_id)
    if score is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return score
