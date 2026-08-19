import os
import unittest
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.collectors.base import Collector
from app.collectors.manual import ManualCollector
from app.core.database import SessionLocal, engine
from app.main import app
from app.models import (
    Base,
    CollectionRunStatus,
    EventType,
    Listing,
    ListingEvent,
    ListingSourceRecord,
    MarketStatus,
)
from app.schemas.ingestion import RawListing
from app.services.collection import run_collector
from app.services.raw_normalizer import normalize_raw_listing


class FailingCollector(Collector):
    @property
    def name(self) -> str:
        return "failing"

    def collect(self) -> Iterable[RawListing]:
        raise RuntimeError("source unavailable")


class ReconcilingCollector(Collector):
    supports_reconciliation = True

    def __init__(self, items: Iterable[RawListing]) -> None:
        self._items = tuple(items)

    @property
    def name(self) -> str:
        return "reconciling-source"

    def collect(self) -> Iterable[RawListing]:
        return iter(self._items)


class IngestionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.headers = {"X-Internal-API-Key": "test-internal-key"}

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def test_raw_normalizer_parses_business_fields_without_guessing(self) -> None:
        raw = RawListing(
            source="manual",
            source_url="https://example.com/manual/1",
            collected_at=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
            payload={
                "title": "Restaurant space",
                "city": "San Mateo",
                "asking_price": "$239K",
                "monthly_rent": "$6,500",
                "size_sqft": "1,800 sqft",
                "seats": "80 seats",
                "lng": "-122.325",
                "lat": "37.563",
                "type1_hood": "yes",
                "parking": "not stated",
                "market_status": "for sale",
            },
        )

        observation = normalize_raw_listing(raw)
        self.assertEqual(observation.asking_price, Decimal("239000"))
        self.assertEqual(observation.monthly_rent, Decimal("6500"))
        self.assertEqual(observation.size_sqft, 1800)
        self.assertEqual(observation.seats, 80)
        self.assertEqual(observation.lng, -122.325)
        self.assertTrue(observation.type1_hood)
        self.assertIsNone(observation.parking)
        self.assertEqual(observation.market_status.value, "ACTIVE")

    def test_manual_import_persists_successes_and_failures(self) -> None:
        request = {
            "items": [
                {
                    "source_url": "https://example.com/manual/1",
                    "external_id": "manual-1",
                    "payload": {
                        "title": "Restaurant space",
                        "city": "San Mateo",
                        "address": "100 Main Street",
                        "asking_price": "$239K",
                        "monthly_rent": "$6,500",
                        "size_sqft": "1,800 sqft",
                        "market_status": "active",
                    },
                },
                {
                    "source_url": "https://example.com/manual/bad",
                    "payload": {"city": "San Mateo", "asking_price": "call broker"},
                },
            ]
        }

        unauthorized = self.client.post("/api/jobs/manual", json=request)
        self.assertEqual(unauthorized.status_code, 401)

        response = self.client.post(
            "/api/jobs/manual", json=request, headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        run = response.json()
        self.assertEqual(run["status"], "PARTIAL")
        self.assertEqual(run["collected_count"], 2)
        self.assertEqual(run["succeeded_count"], 1)
        self.assertEqual(run["failed_count"], 1)

        items = self.client.get(
            f"/api/jobs/runs/{run['id']}/items", headers=self.headers
        )
        self.assertEqual(items.status_code, 200)
        payload = items.json()
        self.assertEqual({item["status"] for item in payload}, {"INGESTED", "FAILED"})
        failed_item = next(item for item in payload if item["status"] == "FAILED")
        self.assertIn("Missing required field: title", failed_item["error_message"])

        listings = self.client.get("/api/listings")
        self.assertEqual(listings.status_code, 200)
        self.assertEqual(len(listings.json()), 1)

    def test_collector_level_failure_is_recorded(self) -> None:
        with SessionLocal() as db:
            run = run_collector(db, FailingCollector())
            self.assertEqual(run.status, CollectionRunStatus.FAILED)
            self.assertEqual(run.collected_count, 0)
            self.assertEqual(run.succeeded_count, 0)
            self.assertEqual(run.failed_count, 0)
            self.assertEqual(run.error_summary, "source unavailable")

    def test_automated_scan_is_protected_and_disabled_by_default(self) -> None:
        request = {"collector": "restaurant_realty"}
        unauthorized = self.client.post("/api/jobs/scan", json=request)
        self.assertEqual(unauthorized.status_code, 401)

        with patch(
            "app.services.jobs.get_settings",
            return_value=SimpleNamespace(restaurant_realty_enabled=False),
        ):
            response = self.client.post(
                "/api/jobs/scan", json=request, headers=self.headers
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("RESTAURANT_REALTY_ENABLED=true", response.json()["detail"])

    def test_successful_scans_reconcile_removal_and_reappearance(self) -> None:
        raw = RawListing(
            source="reconciling-source",
            source_url="https://example.com/listings/reconcile-1",
            external_id="reconcile-1",
            payload={
                "title": "Palo Alto restaurant opportunity",
                "city": "Palo Alto",
                "asking_price": "150000",
                "market_status": "active",
            },
        )

        with SessionLocal() as db:
            first = run_collector(db, ReconcilingCollector([raw]))
            listing_id = db.scalar(select(Listing.id))
            self.assertEqual(first.status, CollectionRunStatus.COMPLETED)
            self.assertEqual(first.reconciled_count, 0)

            first_miss = run_collector(db, ReconcilingCollector([]))
            listing = db.get(Listing, listing_id)
            source_record = db.scalar(select(ListingSourceRecord))
            self.assertEqual(first_miss.reconciled_count, 1)
            self.assertEqual(first_miss.source_removed_count, 0)
            self.assertEqual(source_record.missed_scan_count, 1)
            self.assertEqual(listing.market_status, MarketStatus.ACTIVE)

            second_miss = run_collector(db, ReconcilingCollector([]))
            listing = db.get(Listing, listing_id)
            source_record = db.scalar(select(ListingSourceRecord))
            self.assertEqual(second_miss.source_removed_count, 1)
            self.assertEqual(second_miss.listing_removed_count, 1)
            self.assertIsNotNone(source_record.removed_at)
            self.assertEqual(listing.market_status, MarketStatus.OFF_MARKET)

            reappeared = run_collector(db, ReconcilingCollector([raw]))
            listing = db.get(Listing, listing_id)
            source_record = db.scalar(select(ListingSourceRecord))
            event_types = set(db.scalars(select(ListingEvent.event_type)))
            self.assertEqual(reappeared.status, CollectionRunStatus.COMPLETED)
            self.assertEqual(source_record.missed_scan_count, 0)
            self.assertIsNone(source_record.removed_at)
            self.assertEqual(listing.market_status, MarketStatus.ACTIVE)
            self.assertIn(EventType.LISTING_REMOVED, event_types)
            self.assertIn(EventType.BACK_ON_MARKET, event_types)

    def test_reconciliation_preserves_listing_with_an_available_second_source(self) -> None:
        first_source = RawListing(
            source="reconciling-source",
            source_url="https://example.com/listings/multi-source",
            external_id="multi-source-a",
            payload={
                "title": "Downtown restaurant opportunity",
                "address": "100 University Avenue",
                "city": "Palo Alto",
                "market_status": "active",
            },
        )
        second_source = first_source.model_copy(
            update={
                "source": "other-source",
                "source_url": "https://broker.example/multi-source",
                "external_id": "multi-source-b",
            }
        )

        with SessionLocal() as db:
            run_collector(db, ReconcilingCollector([first_source]))
            run_collector(db, ManualCollector([second_source]))
            listing_id = db.scalar(select(Listing.id))

            run_collector(db, ReconcilingCollector([]))
            second_miss = run_collector(db, ReconcilingCollector([]))
            listing = db.get(Listing, listing_id)
            source_records = list(db.scalars(select(ListingSourceRecord)))

            self.assertEqual(second_miss.source_removed_count, 1)
            self.assertEqual(second_miss.listing_removed_count, 0)
            self.assertEqual(listing.market_status, MarketStatus.ACTIVE)
            self.assertEqual(
                {record.source: record.market_status for record in source_records},
                {
                    "reconciling-source": MarketStatus.OFF_MARKET,
                    "other-source": MarketStatus.ACTIVE,
                },
            )


if __name__ == "__main__":
    unittest.main()
