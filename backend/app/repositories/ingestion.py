import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.ingestion import CollectionRun, RawListingRecord


def list_runs(db: Session, *, offset: int, limit: int) -> list[CollectionRun]:
    statement: Select[tuple[CollectionRun]] = (
        select(CollectionRun)
        .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def get_run(db: Session, run_id: uuid.UUID) -> CollectionRun | None:
    return db.get(CollectionRun, run_id)


def list_run_items(db: Session, run_id: uuid.UUID) -> list[RawListingRecord]:
    return list(
        db.scalars(
            select(RawListingRecord)
            .where(RawListingRecord.run_id == run_id)
            .order_by(RawListingRecord.created_at, RawListingRecord.id)
        )
    )
