import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_internal_api_key
from app.core.database import get_db
from app.models.external_lead import ExternalLeadSource, ExternalLeadStatus
from app.schemas.external_lead import (
    ExternalLeadCreate,
    ExternalLeadRead,
    ExternalLeadUpdate,
)
from app.services import external_leads as service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ExternalLeadRead])
def list_external_leads(
    db: DbSession,
    source: ExternalLeadSource | None = None,
    status_filter: Annotated[
        ExternalLeadStatus | None, Query(alias="status")
    ] = None,
    city: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ExternalLeadRead]:
    return service.find_external_leads(
        db,
        source=source,
        status=status_filter,
        city=city,
        offset=offset,
        limit=limit,
    )


@router.post(
    "", response_model=ExternalLeadRead, dependencies=[Depends(require_internal_api_key)]
)
def create_external_lead(
    request: ExternalLeadCreate, db: DbSession
) -> ExternalLeadRead:
    try:
        return service.add_external_lead(db, request)
    except (service.ExternalLeadUrlError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{lead_id}",
    response_model=ExternalLeadRead,
    dependencies=[Depends(require_internal_api_key)],
)
def update_external_lead(
    lead_id: uuid.UUID, update: ExternalLeadUpdate, db: DbSession
) -> ExternalLeadRead:
    lead = service.find_external_lead(db, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="External lead not found"
        )
    try:
        return service.apply_external_lead_update(db, lead, update)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
