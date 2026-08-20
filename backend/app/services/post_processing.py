import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ingestion import CollectionRun
from app.services import intelligence, notifications

logger = logging.getLogger(__name__)


def process_collection_run(db: Session, run: CollectionRun) -> None:
    settings = get_settings()
    listing_ids = notifications.listing_ids_for_run(db, run.id)
    if settings.openai_enabled:
        intelligence.generate_for_listing_ids(db, listing_ids)
    if settings.alert_recipient:
        notifications.process_collection_run(db, run, settings=settings)
