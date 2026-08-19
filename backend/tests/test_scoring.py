import os
import unittest
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"

from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base, Listing
from app.services.scoring import calculate_scores


class ScoringTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def _listing(self, **changes: object) -> Listing:
        values = {
            "title": "Second-generation restaurant",
            "city": "Palo Alto",
            "asking_price": Decimal("250000"),
            "monthly_rent": Decimal("6500"),
            "size_sqft": 1800,
            "seats": 70,
            "parking": True,
            "loading_access": True,
            "type1_hood": True,
            "grease_trap": True,
            "walk_in_cooler": True,
            "source": "manual",
            "source_url": "https://example.com/score-1",
        }
        values.update(changes)
        return Listing(**values)

    def test_deterministic_scores_are_separate_and_bounded(self) -> None:
        result = calculate_scores(self._listing())
        self.assertEqual(result["corporate_catering_score"], 100.0)
        self.assertGreater(result["restaurant_score"], 0)
        self.assertLessEqual(result["restaurant_score"], 100)
        self.assertGreater(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)
        self.assertIn("competition_data", result["missing_information"])

    def test_unknowns_reduce_completeness_instead_of_becoming_zero(self) -> None:
        full = calculate_scores(self._listing())
        sparse = calculate_scores(
            self._listing(
                monthly_rent=None,
                size_sqft=None,
                seats=None,
                parking=None,
                loading_access=None,
                type1_hood=None,
                grease_trap=None,
                walk_in_cooler=None,
            )
        )
        self.assertEqual(sparse["corporate_catering_score"], 100.0)
        self.assertIsNone(sparse["restaurant_score"])
        self.assertIsNone(sparse["overall_score"])
        self.assertLess(
            sparse["corporate_completeness"], full["corporate_completeness"]
        )
        self.assertIn("monthly_rent", sparse["missing_information"])

    def test_scores_api_calculates_persists_and_returns_factor_detail(self) -> None:
        with SessionLocal() as db:
            listing = self._listing()
            db.add(listing)
            db.commit()
            db.refresh(listing)
            listing_id = str(listing.id)

        response = self.client.get(f"/api/listings/{listing_id}/scores")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["listing_id"], listing_id)
        self.assertIn("rent_economics", payload["corporate_factors"])
        self.assertEqual(payload["config_version"], "v1-default")

        detail = self.client.get(f"/api/listings/{listing_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNotNone(detail.json()["overall_score"])

    def test_scores_api_returns_not_found(self) -> None:
        response = self.client.get(
            "/api/listings/00000000-0000-0000-0000-000000000000/scores"
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
