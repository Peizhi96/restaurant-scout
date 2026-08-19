import logging

from app.core.database import SessionLocal
from app.models.ingestion import CollectionRun
from app.schemas.ingestion import AutomatedCollectorName, AutomatedScanRequest
from app.services import jobs as job_service

logger = logging.getLogger(__name__)


def run_daily_scan() -> CollectionRun:
    request = AutomatedScanRequest(
        collector=AutomatedCollectorName.RESTAURANT_REALTY
    )
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_daily_scan()


if __name__ == "__main__":
    main()
