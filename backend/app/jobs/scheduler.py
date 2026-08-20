import logging
import time
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.jobs.daily_scan import run_daily_scans
from app.services.jobs import CollectorDisabledError

logger = logging.getLogger(__name__)


def next_daily_run(
    now: datetime,
    *,
    timezone_name: str,
    hour: int,
    minute: int,
) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    timezone = ZoneInfo(timezone_name)
    local_now = now.astimezone(timezone)
    run_at = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= local_now:
        run_at += timedelta(days=1)
    return run_at


def seconds_until(now: datetime, run_at: datetime) -> float:
    if now.tzinfo is None or run_at.tzinfo is None:
        raise ValueError("scheduler timestamps must be timezone-aware")
    return max(
        0.0,
        (
            run_at.astimezone(UTC) - now.astimezone(UTC)
        ).total_seconds(),
    )


def run_scheduler() -> None:
    settings = get_settings()
    while True:
        now = datetime.now(UTC)
        run_at = next_daily_run(
            now,
            timezone_name=settings.scheduler_timezone,
            hour=settings.scheduler_daily_hour,
            minute=settings.scheduler_daily_minute,
        )
        wait_seconds = seconds_until(now, run_at)
        logger.info(
            "Next daily scan scheduled for %s (in %.0f seconds)",
            run_at.strftime("%Y-%m-%d %I:%M %p %Z"),
            wait_seconds,
        )
        time.sleep(wait_seconds)

        try:
            run_daily_scans()
        except CollectorDisabledError as exc:
            logger.warning("Scheduled scan skipped: %s", exc)
        except Exception:
            logger.exception("Scheduled scan failed")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_scheduler()


if __name__ == "__main__":
    main()
