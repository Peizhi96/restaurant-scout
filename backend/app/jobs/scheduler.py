import logging
import time
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.jobs.daily_scan import enabled_collectors, run_daily_scans
from app.models.external_lead import (
    ExternalLeadSource,
    ExternalLeadSyncRun,
    ExternalLeadSyncStatus,
)
from app.models.ingestion import CollectionRun, CollectionRunStatus
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


def scheduled_run_today(
    now: datetime,
    *,
    timezone_name: str,
    hour: int,
    minute: int,
) -> datetime | None:
    """Return today's scheduled instant only when it has already been missed."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    timezone = ZoneInfo(timezone_name)
    local_now = now.astimezone(timezone)
    run_at = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return run_at if run_at <= local_now else None


def scheduled_cycle_completed_since(since: datetime, settings: Settings) -> bool:
    """Check each enabled listing source; email is checked only in email-only mode."""
    collectors = enabled_collectors(settings)
    with SessionLocal() as db:
        if collectors:
            for collector in collectors:
                completed = db.scalar(
                    select(CollectionRun.id)
                    .where(
                        CollectionRun.collector_name == collector.value,
                        CollectionRun.status == CollectionRunStatus.COMPLETED,
                        CollectionRun.completed_at >= since,
                    )
                    .limit(1)
                )
                if completed is None:
                    return False
            return True
        if settings.bizbuysell_email_alerts_enabled:
            completed = db.scalar(
                select(ExternalLeadSyncRun.id)
                .where(
                    ExternalLeadSyncRun.source == ExternalLeadSource.BIZBUYSELL,
                    ExternalLeadSyncRun.status == ExternalLeadSyncStatus.SUCCEEDED,
                    ExternalLeadSyncRun.completed_at >= since,
                )
                .limit(1)
            )
            return completed is not None
    return True


def _run_scheduled_cycle(label: str) -> None:
    try:
        run_daily_scans()
    except CollectorDisabledError as exc:
        logger.warning("%s skipped: %s", label, exc)
    except Exception:
        logger.exception("%s failed", label)


def run_scheduler() -> None:
    settings = get_settings()
    startup_time = datetime.now(UTC)
    missed_run = scheduled_run_today(
        startup_time,
        timezone_name=settings.scheduler_timezone,
        hour=settings.scheduler_daily_hour,
        minute=settings.scheduler_daily_minute,
    )
    if missed_run is not None and not scheduled_cycle_completed_since(
        missed_run.astimezone(UTC), settings
    ):
        logger.info(
            "Today's %s scheduled scan was missed; starting catch-up now",
            missed_run.strftime("%I:%M %p %Z"),
        )
        _run_scheduled_cycle("Startup catch-up scan")

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

        _run_scheduled_cycle("Scheduled scan")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_scheduler()


if __name__ == "__main__":
    main()
