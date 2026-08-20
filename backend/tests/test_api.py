import os
import unittest
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base, Listing, ListingStatus


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            listing = Listing(
                title="Second-generation restaurant near downtown",
                business_name=None,
                address="100 Main St",
                city="San Mateo",
                zip="94401",
                asking_price=Decimal("250000.00"),
                monthly_rent=Decimal("6500.00"),
                size_sqft=1800,
                parking=True,
                loading_access=None,
                type1_hood=True,
                source="manual",
                source_url="https://example.com/listings/1",
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)
            self.listing_id = str(listing.id)

    def test_health_and_readiness(self) -> None:
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/readyz").json(), {"status": "ready"})

    def test_list_and_filter_listings(self) -> None:
        response = self.client.get(
            "/api/listings",
            params={"city": "san mateo", "type1_hood": "true", "max_monthly_rent": 8000},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], self.listing_id)
        self.assertEqual(payload[0]["status"], "NEW")

        no_matches = self.client.get("/api/listings", params={"city": "Sunnyvale"})
        self.assertEqual(no_matches.status_code, 200)
        self.assertEqual(no_matches.json(), [])

    def test_get_and_update_listing(self) -> None:
        detail = self.client.get(f"/api/listings/{self.listing_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["city"], "San Mateo")

        updated = self.client.patch(
            f"/api/listings/{self.listing_id}",
            json={"status": ListingStatus.CONTACT_BROKER.value, "notes": "Call broker Tuesday"},
            headers={"X-Internal-API-Key": "test-internal-key"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "CONTACT_BROKER")
        self.assertEqual(updated.json()["notes"], "Call broker Tuesday")

    def test_not_found_and_empty_patch(self) -> None:
        missing = self.client.get("/api/listings/00000000-0000-0000-0000-000000000000")
        self.assertEqual(missing.status_code, 404)

        empty_patch = self.client.patch(
            f"/api/listings/{self.listing_id}",
            json={},
            headers={"X-Internal-API-Key": "test-internal-key"},
        )
        self.assertEqual(empty_patch.status_code, 422)

        null_status = self.client.patch(
            f"/api/listings/{self.listing_id}",
            json={"status": None},
            headers={"X-Internal-API-Key": "test-internal-key"},
        )
        self.assertEqual(null_status.status_code, 422)


if __name__ == "__main__":
    unittest.main()
