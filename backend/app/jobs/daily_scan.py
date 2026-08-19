import logging

from app.core.database import SessionLocal
from app.models.ingestion import CollectionRun
from app.schemas.ingestion import AutomatedCollectorName, AutomatedScanRequest
from app.services import jobs as job_service

logger = logging.getLogger(__name__)


def run_daily_scan(
    collector_name: AutomatedCollectorName = AutomatedCollectorName.RESTAURANT_REALTY,
) -> CollectionRun:
    request = AutomatedScanRequest(collector=collector_name)
    with SessionLocal() as db:
        run = job_service.run_automated_scan(db, request)
        logger.info(
            "Collection run %s finished: status=%s collected=%s failed=%s removed=%s",
            run.id,
            run.status.value,
            run.collected_count,
            run.failed_count,
            run.listing_removed_count,
        )
        return run


def run_daily_scans() -> list[CollectionRun]:
    settings = job_service.get_settings()
    enabled: list[AutomatedCollectorName] = []
    if settings.restaurant_realty_enabled:
        enabled.append(AutomatedCollectorName.RESTAURANT_REALTY)
    if settings.restaurant_for_sales_enabled:
        enabled.append(AutomatedCollectorName.RESTAURANT_FOR_SALES)
    if not enabled:
        raise job_service.CollectorDisabledError("No automated collectors are enabled")
    return [run_daily_scan(name) for name in enabled]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_daily_scans()


if __name__ == "__main__":
    main()
