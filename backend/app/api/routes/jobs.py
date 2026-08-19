import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_internal_api_key
from app.core.database import get_db
from app.schemas.ingestion import (
    AutomatedScanRequest,
    CollectionRunRead,
    ManualIngestionRequest,
    RawListingRecordRead,
)
from app.services import jobs as service

router = APIRouter(dependencies=[Depends(require_internal_api_key)])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/manual", response_model=CollectionRunRead)
def manual_ingestion(
    request: ManualIngestionRequest, db: DbSession
) -> CollectionRunRead:
    return service.run_manual_ingestion(db, request)


@router.post("/scan", response_model=CollectionRunRead)
def automated_scan(request: AutomatedScanRequest, db: DbSession) -> CollectionRunRead:
    try:
        return service.run_automated_scan(db, request)
    except service.CollectorDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/runs", response_model=list[CollectionRunRead])
def list_collection_runs(
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[CollectionRunRead]:
    return service.collection_runs(db, offset=offset, limit=limit)


@router.get("/runs/{run_id}", response_model=CollectionRunRead)
def get_collection_run(run_id: uuid.UUID, db: DbSession) -> CollectionRunRead:
    run = service.collection_run(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection run not found",
        )
    return run


@router.get("/runs/{run_id}/items", response_model=list[RawListingRecordRead])
def get_collection_run_items(
    run_id: uuid.UUID, db: DbSession
) -> list[RawListingRecordRead]:
    if service.collection_run(db, run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection run not found",
        )
    return service.collection_run_items(db, run_id)
