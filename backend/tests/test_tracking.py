import os
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import (
    Base,
    DuplicateReviewStatus,
    EventType,
    Listing,
    ListingEvent,
    ListingSnapshot,
    ListingSourceRecord,
    MarketStatus,
    MatchMethod,
    PossibleDuplicate,
)
from app.schemas.listing import ListingObservation
from app.services.tracking import ingest_observation


class TrackingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.started_at = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)

    def observation(self, **overrides: object) -> ListingObservation:
        payload: dict[str, object] = {
            "title": "Second-generation restaurant near downtown",
            "description": "Type 1 hood and walk-in cooler",
            "address": "100 South Main Street, Suite #12",
            "city": "San Mateo",
            "asking_price": Decimal("250000.00"),
            "monthly_rent": Decimal("6500.00"),
            "size_sqft": 1800,
            "type1_hood": True,
            "source": "broker-site",
            "source_url": "https://www.example.com/listings/1?utm_source=email",
            "external_id": "listing-1",
            "market_status": MarketStatus.ACTIVE,
            "captured_at": self.started_at,
            "raw_payload": {"source_status": "active"},
        }
        payload.update(overrides)
        return ListingObservation.model_validate(payload)

    def test_canonical_url_snapshots_and_change_events(self) -> None:
        with SessionLocal() as db:
            first = ingest_observation(db, self.observation())
            listing_id = first.listing.id
            self.assertEqual(first.match_method, MatchMethod.NEW)
            self.assertEqual([event.event_type for event in first.events], [EventType.NEW_LISTING])

            second = ingest_observation(
                db,
                self.observation(
                    asking_price=Decimal("219000.00"),
                    monthly_rent=Decimal("7000.00"),
                    source_url="http://example.com/listings/1",
                    market_status=MarketStatus.OFF_MARKET,
                    captured_at=self.started_at + timedelta(days=14),
                ),
            )
            self.assertEqual(second.listing.id, listing_id)
            self.assertEqual(second.match_method, MatchMethod.CANONICAL_URL)
            self.assertEqual(
                {event.event_type for event in second.events},
                {EventType.PRICE_DROP, EventType.RENT_CHANGE, EventType.LISTING_REMOVED},
            )

            third = ingest_observation(
                db,
                self.observation(
                    asking_price=Decimal("219000.00"),
                    monthly_rent=Decimal("7000.00"),
                    source_url="https://example.com/listings/1",
                    market_status=MarketStatus.ACTIVE,
                    captured_at=self.started_at + timedelta(days=21),
                ),
            )
            self.assertEqual(
                [event.event_type for event in third.events], [EventType.BACK_ON_MARKET]
            )

            snapshot_count = db.scalar(
                select(func.count()).select_from(ListingSnapshot).where(
                    ListingSnapshot.listing_id == listing_id
                )
            )
            event_count = db.scalar(
                select(func.count()).select_from(ListingEvent).where(
                    ListingEvent.listing_id == listing_id
                )
            )
            self.assertEqual(snapshot_count, 3)
            self.assertEqual(event_count, 5)

        history = self.client.get(f"/api/listings/{listing_id}/history")
        events = self.client.get(f"/api/listings/{listing_id}/events")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 3)
        self.assertEqual(events.status_code, 200)
        self.assertEqual(len(events.json()), 5)

    def test_normalized_address_merges_multiple_sources(self) -> None:
        with SessionLocal() as db:
            first = ingest_observation(db, self.observation())
            second = ingest_observation(
                db,
                self.observation(
                    source="search",
                    source_url="https://search.example/items/abc",
                    external_id="abc",
                    address="100 S Main St Ste 12",
                    captured_at=self.started_at + timedelta(hours=2),
                ),
            )

            self.assertEqual(second.match_method, MatchMethod.NORMALIZED_ADDRESS)
            self.assertEqual(second.listing.id, first.listing.id)
            source_count = db.scalar(
                select(func.count()).select_from(ListingSourceRecord).where(
                    ListingSourceRecord.listing_id == first.listing.id
                )
            )
            self.assertEqual(source_count, 2)

    def test_high_confidence_fuzzy_match_auto_merges(self) -> None:
        with SessionLocal() as db:
            first = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="500 Castro Street",
                    source_url="https://broker.example/500-castro",
                    external_id="500-castro",
                ),
            )
            matched = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="502 Castro Street",
                    source="search",
                    source_url="https://search.example/502-castro",
                    external_id="502-castro",
                    captured_at=self.started_at + timedelta(hours=1),
                ),
            )

            self.assertEqual(matched.match_method, MatchMethod.FUZZY)
            self.assertEqual(matched.listing.id, first.listing.id)
            self.assertIsNone(matched.possible_duplicate)

    def test_fuzzy_review_can_be_kept_separate(self) -> None:
        with SessionLocal() as db:
            first = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="500 Castro Street",
                    source_url="https://broker.example/500-castro",
                    external_id="500-castro",
                ),
            )
            review_result = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="700 Castro Street",
                    asking_price=Decimal("200000.00"),
                    monthly_rent=Decimal("5200.00"),
                    size_sqft=1440,
                    source="search",
                    source_url="https://search.example/700-castro",
                    external_id="700-castro",
                    captured_at=self.started_at + timedelta(hours=1),
                ),
            )

            self.assertEqual(review_result.match_method, MatchMethod.REVIEW)
            self.assertNotEqual(review_result.listing.id, first.listing.id)
            self.assertIsNotNone(review_result.possible_duplicate)
            review_id = review_result.possible_duplicate.id
            review_listing_id = review_result.listing.id
            self.assertEqual(review_result.events, [])

        queue = self.client.get("/api/possible-duplicates")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(len(queue.json()), 1)

        resolved = self.client.patch(
            f"/api/possible-duplicates/{review_id}",
            json={"action": "KEEP_SEPARATE"},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], DuplicateReviewStatus.DISTINCT.value)

        events = self.client.get(f"/api/listings/{review_listing_id}/events")
        self.assertEqual(events.status_code, 200)
        self.assertEqual([item["event_type"] for item in events.json()], ["NEW_LISTING"])

    def test_fuzzy_review_merge_tombstones_duplicate(self) -> None:
        with SessionLocal() as db:
            first = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="500 Castro Street",
                    source_url="https://broker.example/500-castro",
                    external_id="500-castro",
                ),
            )
            review_result = ingest_observation(
                db,
                self.observation(
                    title="Restaurant opportunity downtown",
                    address="700 Castro Street",
                    asking_price=Decimal("200000.00"),
                    monthly_rent=Decimal("5200.00"),
                    size_sqft=1440,
                    source="search",
                    source_url="https://search.example/700-castro",
                    external_id="700-castro",
                    captured_at=self.started_at + timedelta(hours=1),
                ),
            )
            canonical_id = first.listing.id
            duplicate_id = review_result.listing.id
            review_id = review_result.possible_duplicate.id

        resolved = self.client.patch(
            f"/api/possible-duplicates/{review_id}", json={"action": "MERGE"}
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], DuplicateReviewStatus.MERGED.value)

        with SessionLocal() as db:
            duplicate = db.get(Listing, duplicate_id)
            self.assertTrue(duplicate.is_duplicate)
            self.assertEqual(duplicate.merged_into_id, canonical_id)
            source_count = db.scalar(
                select(func.count()).select_from(ListingSourceRecord).where(
                    ListingSourceRecord.listing_id == canonical_id
                )
            )
            self.assertEqual(source_count, 2)
            review = db.get(PossibleDuplicate, review_id)
            self.assertEqual(review.status, DuplicateReviewStatus.MERGED)

        visible = self.client.get("/api/listings")
        self.assertEqual(len(visible.json()), 1)


if __name__ == "__main__":
    unittest.main()
