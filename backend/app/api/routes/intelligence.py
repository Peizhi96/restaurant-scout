import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_internal_api_key
from app.core.database import get_db
from app.schemas.intelligence import (
    AIAnalysisGenerateRequest,
    ListingAIAnalysisRead,
)
from app.services import intelligence as service
from app.services import listings as listing_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{listing_id}/analysis", response_model=ListingAIAnalysisRead)
def get_listing_analysis(listing_id: uuid.UUID, db: DbSession) -> ListingAIAnalysisRead:
    if listing_service.find_listing(db, listing_id) is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    analysis = service.get_analysis(db, listing_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="AI analysis not generated")
    return analysis


@router.post(
    "/{listing_id}/analysis/generate",
    response_model=ListingAIAnalysisRead,
    dependencies=[Depends(require_internal_api_key)],
)
def generate_listing_analysis(
    listing_id: uuid.UUID, request: AIAnalysisGenerateRequest, db: DbSession
) -> ListingAIAnalysisRead:
    listing = listing_service.find_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    try:
        return service.generate_analysis(db, listing, force=request.force)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
