import uuid

from sqlalchemy.orm import Session

from app.collectors.base import Collector
from app.collectors.bizbuysell import BizBuySellCollector
from app.collectors.loopnet import LoopNetCollector
from app.collectors.manual import ManualCollector
from app.collectors.restaurant_for_sales import RestaurantForSalesCollector
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
from app.services.post_processing import process_collection_run


class CollectorDisabledError(RuntimeError):
    pass


def _require_authorized_feed(
    *,
    source_label: str,
    enabled: bool,
    license_confirmed: bool,
    feed_url: str | None,
) -> str:
    env_prefix = source_label.upper()
    if not enabled:
        raise CollectorDisabledError(
            f"{source_label} collector is disabled; set {env_prefix}_ENABLED=true "
            "only after an authorized feed is configured"
        )
    if not license_confirmed:
        raise CollectorDisabledError(
            f"{source_label} collector requires written data permission; set "
            f"{env_prefix}_DATA_LICENSE_CONFIRMED=true only after permission allows "
            "automated access and database storage"
        )
    if feed_url is None:
        raise CollectorDisabledError(
            f"{source_label} collector requires {env_prefix}_AUTHORIZED_FEED_URL"
        )
    return feed_url


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
    run = run_collector(db, collector)
    process_collection_run(db, run)
    return run


def _run_with_post_processing(db: Session, collector: Collector) -> CollectionRun:
    run = run_collector(db, collector)
    process_collection_run(db, run)
    return run


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
        return _run_with_post_processing(db, collector)
    if request.collector == AutomatedCollectorName.RESTAURANT_FOR_SALES:
        if not settings.restaurant_for_sales_enabled:
            raise CollectorDisabledError(
                "RestaurantForSales collector is disabled; set "
                "RESTAURANT_FOR_SALES_ENABLED=true to enable it"
            )
        collector = RestaurantForSalesCollector(
            site_url=settings.restaurant_for_sales_site_url,
            target_cities=settings.restaurant_realty_target_cities,
            target_counties=settings.restaurant_realty_target_counties,
            timeout_seconds=settings.restaurant_for_sales_timeout_seconds,
            request_delay_seconds=settings.restaurant_for_sales_request_delay_seconds,
            user_agent=settings.restaurant_for_sales_user_agent,
        )
        return _run_with_post_processing(db, collector)
    if request.collector == AutomatedCollectorName.BIZBUYSELL:
        feed_url = _require_authorized_feed(
            source_label="BIZBUYSELL",
            enabled=settings.bizbuysell_enabled,
            license_confirmed=settings.bizbuysell_data_license_confirmed,
            feed_url=settings.bizbuysell_authorized_feed_url,
        )
        collector = BizBuySellCollector(
            feed_url=feed_url,
            target_cities=settings.restaurant_realty_target_cities,
            feed_is_complete=settings.bizbuysell_feed_is_complete,
            bearer_token=settings.bizbuysell_authorized_feed_token,
            timeout_seconds=settings.bizbuysell_timeout_seconds,
            user_agent=settings.bizbuysell_user_agent,
        )
        return _run_with_post_processing(db, collector)
    if request.collector == AutomatedCollectorName.LOOPNET:
        feed_url = _require_authorized_feed(
            source_label="LOOPNET",
            enabled=settings.loopnet_enabled,
            license_confirmed=settings.loopnet_data_license_confirmed,
            feed_url=settings.loopnet_authorized_feed_url,
        )
        collector = LoopNetCollector(
            feed_url=feed_url,
            target_cities=settings.restaurant_realty_target_cities,
            feed_is_complete=settings.loopnet_feed_is_complete,
            bearer_token=settings.loopnet_authorized_feed_token,
            timeout_seconds=settings.loopnet_timeout_seconds,
            user_agent=settings.loopnet_user_agent,
        )
        return _run_with_post_processing(db, collector)
    raise ValueError(f"Unsupported collector: {request.collector}")


def collection_runs(db: Session, *, offset: int, limit: int) -> list[CollectionRun]:
    return repository.list_runs(db, offset=offset, limit=limit)


def collection_run(db: Session, run_id: uuid.UUID) -> CollectionRun | None:
    return repository.get_run(db, run_id)


def collection_run_items(db: Session, run_id: uuid.UUID) -> list[RawListingRecord]:
    return repository.list_run_items(db, run_id)
