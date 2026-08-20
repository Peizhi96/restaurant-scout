import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.external_lead import (
    ExternalLead,
    ExternalLeadSource,
    ExternalLeadStatus,
    ExternalLeadSyncRun,
    ExternalLeadSyncStatus,
)


def list_external_leads(
    db: Session,
    *,
    source: ExternalLeadSource | None,
    status: ExternalLeadStatus | None,
    city: str | None,
    offset: int,
    limit: int,
) -> list[ExternalLead]:
    query: Select[tuple[ExternalLead]] = select(ExternalLead)
    if source is not None:
        query = query.where(ExternalLead.source == source)
    if status is not None:
        query = query.where(ExternalLead.status == status)
    if city:
        query = query.where(ExternalLead.city.ilike(city.strip()))
    query = query.order_by(ExternalLead.discovered_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(query))


def get_external_lead(db: Session, lead_id: uuid.UUID) -> ExternalLead | None:
    return db.get(ExternalLead, lead_id)


def get_by_canonical_url(db: Session, canonical_url: str) -> ExternalLead | None:
    return db.scalar(
        select(ExternalLead).where(ExternalLead.canonical_url == canonical_url)
    )


def create_external_lead(db: Session, lead: ExternalLead) -> ExternalLead:
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def update_external_lead(
    db: Session,
    lead: ExternalLead,
    *,
    city: str | None,
    status: ExternalLeadStatus | None,
    notes: str | None,
    fields_set: set[str],
) -> ExternalLead:
    if "city" in fields_set:
        lead.city = city
    if "status" in fields_set and status is not None:
        lead.status = status
    if "notes" in fields_set:
        lead.notes = notes
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def create_sync_run(db: Session, run: ExternalLeadSyncRun) -> ExternalLeadSyncRun:
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_sync_run(
    db: Session,
    run: ExternalLeadSyncRun,
    *,
    status: ExternalLeadSyncStatus,
    messages_scanned: int,
    links_found: int,
    leads_created: int,
    leads_existing: int,
    error_message: str | None = None,
) -> ExternalLeadSyncRun:
    run.status = status
    run.messages_scanned = messages_scanned
    run.links_found = links_found
    run.leads_created = leads_created
    run.leads_existing = leads_existing
    run.error_message = error_message
    run.completed_at = datetime.now(UTC)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def latest_sync_run(
    db: Session, source: ExternalLeadSource
) -> ExternalLeadSyncRun | None:
    return db.scalar(
        select(ExternalLeadSyncRun)
        .where(ExternalLeadSyncRun.source == source)
        .order_by(ExternalLeadSyncRun.started_at.desc(), ExternalLeadSyncRun.id.desc())
        .limit(1)
    )
