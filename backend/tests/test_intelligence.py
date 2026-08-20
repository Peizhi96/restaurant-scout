import os
import unittest
from dataclasses import replace
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import AIRecommendation, Base, Listing
from app.schemas.intelligence import AIAnalysisOutput
from app.services.intelligence import generate_analysis


class FakeAnalysisClient:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, payload: dict[str, object]) -> AIAnalysisOutput:
        self.calls += 1
        return AIAnalysisOutput(
            recommendation=AIRecommendation.REVIEW,
            strengths=["Type 1 hood is confirmed"],
            risks=["Monthly rent is unknown"],
            missing_information=["monthly_rent"],
            confidence=Decimal("0.72"),
        )


class IntelligenceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def test_analysis_is_structured_persisted_and_fingerprint_idempotent(self) -> None:
        client = FakeAnalysisClient()
        settings = replace(
            get_settings(), openai_enabled=True, openai_model="test-structured-model"
        )
        with SessionLocal() as db:
            listing = Listing(
                title="Restaurant opportunity",
                city="Palo Alto",
                monthly_rent=None,
                size_sqft=1800,
                type1_hood=True,
                source="manual",
                source_url="https://example.com/listing/ai",
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)

            first = generate_analysis(db, listing, settings=settings, client=client)
            second = generate_analysis(db, listing, settings=settings, client=client)

            self.assertEqual(first.recommendation, AIRecommendation.REVIEW)
            self.assertIn("monthly_rent", first.missing_information)
            self.assertEqual(first.model, "test-structured-model")
            self.assertEqual(second.input_fingerprint, first.input_fingerprint)
            self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
