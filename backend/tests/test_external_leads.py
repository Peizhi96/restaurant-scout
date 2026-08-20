import os
import unittest

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base, ExternalLead


class ExternalLeadApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.auth = {"X-Internal-API-Key": "test-internal-key"}

    def test_create_deduplicate_list_and_update_link_only_lead(self) -> None:
        created = self.client.post(
            "/api/external-leads",
            json={
                "source_url": (
                    "https://www.bizbuysell.com/Business-Opportunity/cafe/123/"
                    "?utm_source=email&msockid=tracking#details"
                ),
                "city": "san mateo",
                "notes": "Review location and contact path.",
            },
            headers=self.auth,
        )
        self.assertEqual(created.status_code, 200)
        lead = created.json()
        self.assertEqual(lead["source"], "BIZBUYSELL")
        self.assertEqual(lead["city"], "San Mateo")
        self.assertEqual(lead["status"], "NEW")
        self.assertEqual(
            lead["source_url"],
            "https://www.bizbuysell.com/Business-Opportunity/cafe/123",
        )
        self.assertNotIn("title", lead)

        duplicate = self.client.post(
            "/api/external-leads",
            json={
                "source_url": (
                    "http://www.bizbuysell.com/Business-Opportunity/cafe/123/"
                    "?utm_campaign=second"
                ),
                "city": "Palo Alto",
            },
            headers=self.auth,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["id"], lead["id"])
        with SessionLocal() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ExternalLead)), 1)

        listed = self.client.get(
            "/api/external-leads", params={"source": "BIZBUYSELL"}
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        updated = self.client.patch(
            f"/api/external-leads/{lead['id']}",
            json={
                "city": "Palo Alto",
                "status": "CONTACT_BROKER",
                "notes": "Ask broker for independently supplied facts.",
            },
            headers=self.auth,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["city"], "Palo Alto")
        self.assertEqual(updated.json()["status"], "CONTACT_BROKER")

    def test_accepts_loopnet_and_filters(self) -> None:
        created = self.client.post(
            "/api/external-leads",
            json={
                "source_url": "https://www.loopnet.com/Listing/example/456/",
                "city": None,
            },
            headers=self.auth,
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["source"], "LOOPNET")
        self.assertIsNone(created.json()["city"])

        matches = self.client.get(
            "/api/external-leads", params={"status": "NEW", "source": "LOOPNET"}
        )
        self.assertEqual(matches.status_code, 200)
        self.assertEqual(len(matches.json()), 1)

        no_matches = self.client.get(
            "/api/external-leads", params={"source": "BIZBUYSELL"}
        )
        self.assertEqual(no_matches.status_code, 200)
        self.assertEqual(no_matches.json(), [])

    def test_rejects_non_source_homepage_and_non_target_city(self) -> None:
        invalid_urls = (
            "https://example.com/listing/1",
            "https://bizbuysell.com.evil.example/listing/1",
            "https://www.loopnet.com/",
        )
        for source_url in invalid_urls:
            with self.subTest(source_url=source_url):
                response = self.client.post(
                    "/api/external-leads",
                    json={"source_url": source_url},
                    headers=self.auth,
                )
                self.assertEqual(response.status_code, 422)

        outside_scope = self.client.post(
            "/api/external-leads",
            json={
                "source_url": "https://www.loopnet.com/Listing/example/789/",
                "city": "Oakland",
            },
            headers=self.auth,
        )
        self.assertEqual(outside_scope.status_code, 422)
        self.assertIn("P0 target cities", outside_scope.json()["detail"])

    def test_update_requires_existing_lead_and_nonempty_payload(self) -> None:
        missing = self.client.patch(
            "/api/external-leads/00000000-0000-0000-0000-000000000000",
            json={"status": "PASSED"},
            headers=self.auth,
        )
        self.assertEqual(missing.status_code, 404)

        created = self.client.post(
            "/api/external-leads",
            json={"source_url": "https://www.loopnet.com/Listing/example/999/"},
            headers=self.auth,
        )
        empty = self.client.patch(
            f"/api/external-leads/{created.json()['id']}",
            json={},
            headers=self.auth,
        )
        self.assertEqual(empty.status_code, 422)


if __name__ == "__main__":
    unittest.main()
