import os
import unittest
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base, Listing


class DueDiligenceApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.read_headers = {"X-Internal-API-Key": "test-internal-key"}
        cls.write_headers = {
            "X-Internal-API-Key": "test-internal-key",
            "X-Operator-Id": "peizhi",
        }

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            listing = Listing(
                title="Confidential restaurant opportunity",
                city="Palo Alto",
                asking_price=Decimal("275000.00"),
                source="manual",
                source_url="https://example.com/listings/confidential-1",
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)
            self.listing_id = str(listing.id)
        self.base_url = f"/api/listings/{self.listing_id}/due-diligence"

    def test_endpoints_require_internal_api_key(self) -> None:
        unauthorized = self.client.get(self.base_url)
        self.assertEqual(unauthorized.status_code, 401)

        summary = self.client.get(self.base_url, headers=self.read_headers)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json(), {"profile": None, "metrics": []})

        missing_operator = self.client.patch(
            f"{self.base_url}/profile",
            json={"access_status": "NDA_REQUIRED"},
            headers=self.read_headers,
        )
        self.assertEqual(missing_operator.status_code, 422)

    def test_external_nda_profile_requires_official_url_and_is_audited(self) -> None:
        invalid = self.client.patch(
            f"{self.base_url}/profile",
            json={
                "access_method": "EXTERNAL_NDA",
                "access_status": "NDA_REQUIRED",
            },
            headers=self.write_headers,
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("official external URL", invalid.json()["detail"])

        created = self.client.patch(
            f"{self.base_url}/profile",
            json={
                "access_method": "EXTERNAL_NDA",
                "access_status": "NDA_REQUIRED",
                "external_url": "https://broker.example/nda/abc",
                "inventory_included": True,
                "ffe_included": None,
                "notes": "Operator must sign personally on the broker site.",
            },
            headers=self.write_headers,
        )
        self.assertEqual(created.status_code, 200)
        profile = created.json()
        self.assertEqual(profile["access_status"], "NDA_REQUIRED")
        self.assertEqual(profile["external_url"], "https://broker.example/nda/abc")
        self.assertTrue(profile["inventory_included"])
        self.assertIsNone(profile["requested_at"])
        self.assertEqual(profile["created_by"], "peizhi")

        requested = self.client.patch(
            f"{self.base_url}/profile",
            json={"access_status": "REQUESTED"},
            headers=self.write_headers,
        )
        self.assertEqual(requested.status_code, 200)
        self.assertIsNotNone(requested.json()["requested_at"])
        self.assertIsNone(requested.json()["received_at"])

        events = self.client.get(
            f"{self.base_url}/events", headers=self.read_headers
        )
        self.assertEqual(events.status_code, 200)
        payload = events.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(
            {item["event_type"] for item in payload},
            {"PROFILE_CREATED", "PROFILE_UPDATED"},
        )
        self.assertTrue(all(item["actor"] == "peizhi" for item in payload))

    def test_broker_contact_profile_requires_a_contact_channel(self) -> None:
        invalid = self.client.patch(
            f"{self.base_url}/profile",
            json={"access_method": "BROKER_CONTACT"},
            headers=self.write_headers,
        )
        self.assertEqual(invalid.status_code, 422)

        valid = self.client.patch(
            f"{self.base_url}/profile",
            json={
                "access_method": "BROKER_CONTACT",
                "broker_contact_email": "broker@example.com",
                "access_status": "REQUESTED",
            },
            headers=self.write_headers,
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["broker_contact_email"], "broker@example.com")

    def test_financial_metrics_validate_values_preserve_periods_and_are_audited(self) -> None:
        before_receipt = self.client.post(
            f"{self.base_url}/metrics",
            json={
                "metric_type": "GROSS_REVENUE",
                "amount": "1000",
                "source": "broker financial package",
            },
            headers=self.write_headers,
        )
        self.assertEqual(before_receipt.status_code, 422)
        self.assertIn("only after confidential data is received", before_receipt.json()["detail"])

        profile = self.client.patch(
            f"{self.base_url}/profile",
            json={
                "access_method": "EXTERNAL_NDA",
                "access_status": "RECEIVED_UNVERIFIED",
                "external_url": "https://broker.example/nda/financials",
            },
            headers=self.write_headers,
        )
        self.assertEqual(profile.status_code, 200)
        self.assertIsNotNone(profile.json()["requested_at"])
        self.assertIsNotNone(profile.json()["received_at"])

        negative_revenue = self.client.post(
            f"{self.base_url}/metrics",
            json={
                "metric_type": "GROSS_REVENUE",
                "amount": "-1000",
                "source": "broker financial package",
            },
            headers=self.write_headers,
        )
        self.assertEqual(negative_revenue.status_code, 422)
        self.assertIn("GROSS_REVENUE cannot be negative", negative_revenue.json()["detail"])

        created = self.client.post(
            f"{self.base_url}/metrics",
            json={
                "metric_type": "CASH_FLOW",
                "amount": "-12500.50",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "source": "broker financial package",
                "source_reference": "2025 P&L, page 4",
            },
            headers=self.write_headers,
        )
        self.assertEqual(created.status_code, 201)
        metric = created.json()
        self.assertEqual(metric["amount"], "-12500.50")
        self.assertEqual(metric["verification_status"], "UNVERIFIED")
        self.assertEqual(metric["created_by"], "peizhi")

        verified = self.client.patch(
            f"{self.base_url}/metrics/{metric['id']}",
            json={
                "verification_status": "VERIFIED",
                "notes": "Matched against the signed financial package.",
            },
            headers=self.write_headers,
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json()["verification_status"], "VERIFIED")

        invalid_period = self.client.patch(
            f"{self.base_url}/metrics/{metric['id']}",
            json={"period_end": "2024-12-31"},
            headers=self.write_headers,
        )
        self.assertEqual(invalid_period.status_code, 422)

        summary = self.client.get(self.base_url, headers=self.read_headers)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(len(summary.json()["metrics"]), 1)
        self.assertEqual(summary.json()["metrics"][0]["verification_status"], "VERIFIED")

        events = self.client.get(
            f"{self.base_url}/events", headers=self.read_headers
        ).json()
        metric_events = {
            item["event_type"]
            for item in events
            if item["event_type"].startswith("METRIC_")
        }
        self.assertEqual(
            metric_events,
            {"METRIC_CREATED", "METRIC_UPDATED"},
        )

    def test_missing_listing_returns_not_found(self) -> None:
        missing_url = (
            "/api/listings/00000000-0000-0000-0000-000000000000/due-diligence"
        )
        response = self.client.get(missing_url, headers=self.read_headers)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
