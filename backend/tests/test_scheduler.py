import unittest
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.jobs.scheduler import next_daily_run, scheduled_run_today, seconds_until


class SchedulerTimingTestCase(unittest.TestCase):
    def test_schedules_same_day_when_before_eight_am_pacific(self) -> None:
        now = datetime(2026, 8, 20, 14, 30, tzinfo=UTC)

        run_at = next_daily_run(
            now,
            timezone_name="America/Los_Angeles",
            hour=8,
            minute=0,
        )

        self.assertEqual(
            run_at,
            datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
        )
        self.assertEqual(seconds_until(now, run_at), 30 * 60)

    def test_schedules_next_day_when_today_run_time_has_passed(self) -> None:
        now = datetime(2026, 8, 20, 15, 1, tzinfo=UTC)

        run_at = next_daily_run(
            now,
            timezone_name="America/Los_Angeles",
            hour=8,
            minute=0,
        )

        self.assertEqual(
            run_at,
            datetime(2026, 8, 21, 8, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
        )

    def test_wait_uses_elapsed_time_across_daylight_saving_change(self) -> None:
        now = datetime(2026, 3, 7, 17, 0, tzinfo=UTC)

        run_at = next_daily_run(
            now,
            timezone_name="America/Los_Angeles",
            hour=8,
            minute=0,
        )

        self.assertEqual(run_at.strftime("%Y-%m-%d %H:%M %Z"), "2026-03-08 08:00 PDT")
        self.assertEqual(seconds_until(now, run_at), 22 * 60 * 60)

    def test_rejects_naive_now(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            next_daily_run(
                datetime(2026, 8, 20, 7, 30),
                timezone_name="America/Los_Angeles",
                hour=8,
                minute=0,
            )

    def test_detects_a_missed_run_after_eight_am_pacific(self) -> None:
        now = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)

        missed = scheduled_run_today(
            now,
            timezone_name="America/Los_Angeles",
            hour=8,
            minute=0,
        )

        self.assertEqual(
            missed,
            datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
        )

    def test_does_not_catch_up_before_todays_run_time(self) -> None:
        now = datetime(2026, 8, 20, 14, 30, tzinfo=UTC)

        self.assertIsNone(
            scheduled_run_today(
                now,
                timezone_name="America/Los_Angeles",
                hour=8,
                minute=0,
            )
        )
