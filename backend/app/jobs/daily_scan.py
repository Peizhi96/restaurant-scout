import logging

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models.ingestion import CollectionRun
from app.schemas.ingestion import AutomatedCollectorName, AutomatedScanRequest
from app.services import jobs as job_service
from app.services.bizbuysell_email_alerts import (
    EmailAlertSyncDisabledError,
    EmailAlertSyncError,
    sync_email_alerts,
)

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


def enabled_collectors(settings: Settings) -> list[AutomatedCollectorName]:
    enabled: list[AutomatedCollectorName] = []
    if settings.restaurant_realty_enabled:
        enabled.append(AutomatedCollectorName.RESTAURANT_REALTY)
    if settings.restaurant_for_sales_enabled:
        enabled.append(AutomatedCollectorName.RESTAURANT_FOR_SALES)
    if settings.bizbuysell_enabled:
        enabled.append(AutomatedCollectorName.BIZBUYSELL)
    if settings.loopnet_enabled:
        enabled.append(AutomatedCollectorName.LOOPNET)
    return enabled


def run_daily_scans() -> list[CollectionRun]:
    settings = job_service.get_settings()
    enabled = enabled_collectors(settings)
    email_alerts_enabled = settings.bizbuysell_email_alerts_enabled
    if not enabled and not email_alerts_enabled:
        raise job_service.CollectorDisabledError("No automated collectors are enabled")
    runs = [run_daily_scan(name) for name in enabled]
    if email_alerts_enabled:
        try:
            with SessionLocal() as db:
                sync_run = sync_email_alerts(db, settings=settings)
                logger.info(
                    "BizBuySell email link sync %s finished: status=%s messages=%s "
                    "links=%s created=%s existing=%s",
                    sync_run.id,
                    sync_run.status.value,
                    sync_run.messages_scanned,
                    sync_run.links_found,
                    sync_run.leads_created,
                    sync_run.leads_existing,
                )
        except (EmailAlertSyncDisabledError, EmailAlertSyncError):
            logger.exception(
                "BizBuySell email link sync failed; completed listing scans remain valid"
            )
    return runs


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_daily_scans()


if __name__ == "__main__":
    main()
