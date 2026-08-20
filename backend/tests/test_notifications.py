import os
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from email.message import EmailMessage

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import (
    Base,
    EventType,
    Listing,
    ListingEvent,
    NotificationPriority,
    NotificationStatus,
)
from app.services.notifications import (
    deliver_notification,
    queue_event_notification,
    queue_high_score_notification,
)
from app.services.scoring import score_listing


class FakeEmailTransport:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class NotificationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def test_high_score_email_is_deduplicated_and_audited(self) -> None:
        settings = replace(
            get_settings(),
            email_enabled=True,
            alert_recipient="operator@example.com",
            alert_from_email="scout@example.com",
            alert_high_score_threshold=90,
            alert_new_score_threshold=80,
        )
        transport = FakeEmailTransport()
        with SessionLocal() as db:
            listing = Listing(
                title="Complete restaurant",
                city="Palo Alto",
                monthly_rent=Decimal("6000"),
                size_sqft=1800,
                seats=70,
                parking=True,
                loading_access=True,
                type1_hood=True,
                grease_trap=True,
                walk_in_cooler=True,
                source="manual",
                source_url="https://example.com/listing/email",
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)
            score_listing(db, listing)
            event = ListingEvent(
                listing_id=listing.id,
                event_type=EventType.NEW_LISTING,
                old_value=None,
                new_value={"source": "manual"},
                detected_at=datetime.now(UTC),
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            first = queue_high_score_notification(db, listing, settings=settings)
            second = queue_high_score_notification(db, listing, settings=settings)

            self.assertIsNotNone(first)
            assert first is not None
            self.assertEqual(first.id, second.id if second else None)
            self.assertEqual(first.priority, NotificationPriority.HIGH)
            delivered = deliver_notification(
                db, first, settings=settings, transport=transport
            )
            self.assertEqual(delivered.status, NotificationStatus.SENT)
            self.assertEqual(len(transport.messages), 1)

    def test_price_drop_threshold_queues_high_priority_email(self) -> None:
        settings = replace(
            get_settings(),
            alert_recipient="operator@example.com",
            alert_from_email="scout@example.com",
            alert_price_drop_percent=10,
        )
        with SessionLocal() as db:
            listing = Listing(
                title="Price drop candidate",
                city="San Mateo",
                source="manual",
                source_url="https://example.com/listing/drop",
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)
            event = ListingEvent(
                listing_id=listing.id,
                event_type=EventType.PRICE_DROP,
                old_value={"asking_price": "250000"},
                new_value={"asking_price": "220000", "drop_percent": 12},
                detected_at=datetime.now(UTC),
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            notification = queue_event_notification(
                db, listing, event, settings=settings
            )

            self.assertIsNotNone(notification)
            assert notification is not None
            self.assertEqual(notification.trigger_type, "PRICE_DROP")
            self.assertEqual(notification.priority, NotificationPriority.HIGH)


if __name__ == "__main__":
    unittest.main()
