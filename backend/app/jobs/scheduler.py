import logging
import time

from app.core.config import get_settings
from app.jobs.daily_scan import run_daily_scan
from app.services.jobs import CollectorDisabledError

logger = logging.getLogger(__name__)


def run_scheduler() -> None:
    settings = get_settings()
    if settings.scheduler_initial_delay_seconds:
        logger.info(
            "Daily scan scheduler starts in %.0f seconds",
            settings.scheduler_initial_delay_seconds,
        )
        time.sleep(settings.scheduler_initial_delay_seconds)

    while True:
        started_at = time.monotonic()
        try:
            run_daily_scan()
        except CollectorDisabledError as exc:
            logger.warning("Scheduled scan skipped: %s", exc)
        except Exception:
            logger.exception("Scheduled scan failed")

        elapsed = time.monotonic() - started_at
        wait_seconds = max(1.0, settings.scheduler_interval_seconds - elapsed)
        logger.info("Next daily scan in %.0f seconds", wait_seconds)
        time.sleep(wait_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_scheduler()


if __name__ == "__main__":
    main()
