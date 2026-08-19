import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_internal_api_key
from app.core.database import get_db
from app.schemas.due_diligence import (
    DueDiligenceEventRead,
    DueDiligenceProfileRead,
    DueDiligenceProfileUpdate,
    DueDiligenceSummaryRead,
    FinancialMetricCreate,
    FinancialMetricRead,
    FinancialMetricUpdate,
)
from app.services import due_diligence as service

router = APIRouter(
    prefix="/api/listings/{listing_id}/due-diligence",
    dependencies=[Depends(require_internal_api_key)],
)
DbSession = Annotated[Session, Depends(get_db)]
OperatorId = Annotated[
    str,
    Header(alias="X-Operator-Id", min_length=1, max_length=200),
]


def _require_listing(db: Session, listing_id: uuid.UUID) -> None:
    if not service.listing_exists(db, listing_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )


def _clean_operator_id(operator_id: str) -> str:
    actor = operator_id.strip()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Operator-Id cannot be blank",
        )
    return actor


@router.get("", response_model=DueDiligenceSummaryRead)
def get_due_diligence(
    listing_id: uuid.UUID, db: DbSession
) -> DueDiligenceSummaryRead:
    _require_listing(db, listing_id)
    return service.due_diligence_summary(db, listing_id)


@router.patch("/profile", response_model=DueDiligenceProfileRead)
def update_due_diligence_profile(
    listing_id: uuid.UUID,
    update: DueDiligenceProfileUpdate,
    db: DbSession,
    operator_id: OperatorId,
) -> DueDiligenceProfileRead:
    _require_listing(db, listing_id)
    try:
        return service.update_profile(
            db, listing_id, update, actor=_clean_operator_id(operator_id)
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/metrics",
    response_model=FinancialMetricRead,
    status_code=status.HTTP_201_CREATED,
)
def create_financial_metric(
    listing_id: uuid.UUID,
    create: FinancialMetricCreate,
    db: DbSession,
    operator_id: OperatorId,
) -> FinancialMetricRead:
    _require_listing(db, listing_id)
    try:
        return service.create_metric(
            db, listing_id, create, actor=_clean_operator_id(operator_id)
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.patch("/metrics/{metric_id}", response_model=FinancialMetricRead)
def update_financial_metric(
    listing_id: uuid.UUID,
    metric_id: uuid.UUID,
    update: FinancialMetricUpdate,
    db: DbSession,
    operator_id: OperatorId,
) -> FinancialMetricRead:
    _require_listing(db, listing_id)
    metric = service.financial_metric(db, listing_id, metric_id)
    if metric is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial metric not found",
        )
    try:
        return service.update_metric(db, metric, update, actor=_clean_operator_id(operator_id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/events", response_model=list[DueDiligenceEventRead])
def list_due_diligence_events(
    listing_id: uuid.UUID, db: DbSession
) -> list[DueDiligenceEventRead]:
    _require_listing(db, listing_id)
    return service.due_diligence_events(db, listing_id)
