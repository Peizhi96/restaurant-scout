import uuid

from sqlalchemy.orm import Session

from app.collectors.manual import ManualCollector
from app.collectors.restaurant_realty import RestaurantRealtyCollector
from app.core.config import get_settings
from app.models.ingestion import CollectionRun, RawListingRecord
from app.repositories import ingestion as repository
from app.schemas.ingestion import (
    AutomatedCollectorName,
    AutomatedScanRequest,
    ManualIngestionRequest,
    RawListing,
)
from app.services.collection import run_collector


class CollectorDisabledError(RuntimeError):
    pass


def run_manual_ingestion(db: Session, request: ManualIngestionRequest) -> CollectionRun:
    collector = ManualCollector(
        RawListing(
            source="manual",
            source_url=item.source_url,
            external_id=item.external_id,
            payload=item.payload,
            collected_at=item.collected_at,
        )
        for item in request.items
    )
    return run_collector(db, collector)


def run_automated_scan(db: Session, request: AutomatedScanRequest) -> CollectionRun:
    settings = get_settings()
    if request.collector == AutomatedCollectorName.RESTAURANT_REALTY:
        if not settings.restaurant_realty_enabled:
            raise CollectorDisabledError(
                "Restaurant Realty collector is disabled; set "
                "RESTAURANT_REALTY_ENABLED=true to enable it"
            )
        collector = RestaurantRealtyCollector(
            site_url=settings.restaurant_realty_site_url,
            api_url=settings.restaurant_realty_api_url,
            target_cities=settings.restaurant_realty_target_cities,
            target_counties=settings.restaurant_realty_target_counties,
            timeout_seconds=settings.restaurant_realty_timeout_seconds,
            request_delay_seconds=settings.restaurant_realty_request_delay_seconds,
            user_agent=settings.restaurant_realty_user_agent,
        )
        return run_collector(db, collector)
    raise ValueError(f"Unsupported collector: {request.collector}")


def collection_runs(db: Session, *, offset: int, limit: int) -> list[CollectionRun]:
    return repository.list_runs(db, offset=offset, limit=limit)


def collection_run(db: Session, run_id: uuid.UUID) -> CollectionRun | None:
    return repository.get_run(db, run_id)


def collection_run_items(db: Session, run_id: uuid.UUID) -> list[RawListingRecord]:
    return repository.list_run_items(db, run_id)
