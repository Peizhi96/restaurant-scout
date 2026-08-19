import uuid
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.collectors.base import Collector
from app.core.config import get_settings
from app.models.ingestion import (
    CollectionRun,
    CollectionRunStatus,
    RawListingRecord,
    RawListingStatus,
)
from app.services.raw_normalizer import normalize_raw_listing
from app.services.scoring import score_listing
from app.services.tracking import ingest_observation, reconcile_missing_source_records


def _run_status(succeeded: int, failed: int, collector_failed: bool) -> CollectionRunStatus:
    if failed == 0 and not collector_failed:
        return CollectionRunStatus.COMPLETED
    if succeeded > 0:
        return CollectionRunStatus.PARTIAL
    return CollectionRunStatus.FAILED


def run_collector(db: Session, collector: Collector) -> CollectionRun:
    run = CollectionRun(collector_name=collector.name)
    db.add(run)
    db.commit()
    db.refresh(run)

    succeeded = 0
    failed = 0
    collector_error: str | None = None
    observed_source_record_ids: set[uuid.UUID] = set()
    reconciled_count = 0
    source_removed_count = 0
    listing_removed_count = 0

    try:
        items = collector.collect()
        for raw in items:
            record = RawListingRecord(
                run_id=run.id,
                source=raw.source,
                external_id=raw.external_id,
                source_url=raw.source_url,
                payload=jsonable_encoder(raw.payload),
                collected_at=raw.collected_at,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            try:
                observation = normalize_raw_listing(raw)
                result = ingest_observation(db, observation)
                score_listing(db, result.listing)
                observed_source_record_ids.add(result.source_record.id)
                record = db.get(RawListingRecord, record.id)
                record.status = RawListingStatus.INGESTED
                record.normalized_payload = jsonable_encoder(
                    observation.model_dump(mode="json")
                )
                record.listing_id = result.listing.id
                record.processed_at = datetime.now(UTC)
                db.add(record)
                db.commit()
                succeeded += 1
            except Exception as exc:
                db.rollback()
                record = db.get(RawListingRecord, record.id)
                record.status = RawListingStatus.FAILED
                record.error_message = str(exc)[:4000]
                record.processed_at = datetime.now(UTC)
                db.add(record)
                db.commit()
                failed += 1
    except Exception as exc:
        db.rollback()
        collector_error = str(exc)[:4000]

    if collector.supports_reconciliation and collector_error is None and failed == 0:
        try:
            reconciliation = reconcile_missing_source_records(
                db,
                source=collector.name,
                observed_source_record_ids=observed_source_record_ids,
                missing_scan_threshold=get_settings().removal_missing_scan_threshold,
            )
            reconciled_count = reconciliation.reconciled_count
            source_removed_count = reconciliation.source_removed_count
            listing_removed_count = reconciliation.listing_removed_count
        except Exception as exc:
            db.rollback()
            collector_error = f"Reconciliation failed: {exc}"[:4000]

    run = db.get(CollectionRun, run.id)
    run.collected_count = succeeded + failed
    run.succeeded_count = succeeded
    run.failed_count = failed
    run.reconciled_count = reconciled_count
    run.source_removed_count = source_removed_count
    run.listing_removed_count = listing_removed_count
    run.error_summary = collector_error
    run.status = _run_status(succeeded, failed, collector_error is not None)
    run.completed_at = datetime.now(UTC)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
