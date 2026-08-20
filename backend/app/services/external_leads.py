import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.external_lead import ExternalLead, ExternalLeadSource, ExternalLeadStatus
from app.repositories import external_leads as repository
from app.schemas.external_lead import ExternalLeadCreate, ExternalLeadUpdate

_TRACKING_QUERY_KEYS = {"msockid", "ref", "source"}


class ExternalLeadUrlError(ValueError):
    pass


def _source_for_host(hostname: str) -> ExternalLeadSource:
    if hostname == "bizbuysell.com" or hostname.endswith(".bizbuysell.com"):
        return ExternalLeadSource.BIZBUYSELL
    if hostname == "loopnet.com" or hostname.endswith(".loopnet.com"):
        return ExternalLeadSource.LOOPNET
    raise ExternalLeadUrlError(
        "External leads currently accept only BizBuySell or LoopNet listing URLs"
    )


def canonicalize_external_lead_url(
    value: str,
) -> tuple[str, str, ExternalLeadSource]:
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ExternalLeadUrlError("Enter a complete HTTP(S) listing URL")
    hostname = parsed.hostname.casefold()
    source = _source_for_host(hostname)
    path = parsed.path or "/"
    if path == "/":
        raise ExternalLeadUrlError("Enter an individual listing URL, not a homepage")
    filtered_query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    normalized = urlunsplit(
        (
            "https",
            hostname,
            path.rstrip("/") or "/",
            urlencode(filtered_query),
            "",
        )
    )
    return normalized, normalized, source


def _target_city(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    cities = {
        city.casefold(): city for city in get_settings().restaurant_realty_target_cities
    }
    city = cities.get(value.strip().casefold())
    if city is None:
        raise ValueError("City must be one of the configured P0 target cities")
    return city


def find_external_leads(
    db: Session,
    *,
    source: ExternalLeadSource | None,
    status: ExternalLeadStatus | None,
    city: str | None,
    offset: int,
    limit: int,
) -> list[ExternalLead]:
    return repository.list_external_leads(
        db,
        source=source,
        status=status,
        city=city,
        offset=offset,
        limit=limit,
    )


def find_external_lead(db: Session, lead_id: uuid.UUID) -> ExternalLead | None:
    return repository.get_external_lead(db, lead_id)


def add_external_lead(db: Session, request: ExternalLeadCreate) -> ExternalLead:
    source_url, canonical_url, source = canonicalize_external_lead_url(request.source_url)
    existing = repository.get_by_canonical_url(db, canonical_url)
    if existing is not None:
        return existing
    lead = ExternalLead(
        source=source,
        source_url=source_url,
        canonical_url=canonical_url,
        city=_target_city(request.city),
        notes=request.notes.strip() if request.notes and request.notes.strip() else None,
    )
    return repository.create_external_lead(db, lead)


def apply_external_lead_update(
    db: Session, lead: ExternalLead, update: ExternalLeadUpdate
) -> ExternalLead:
    city = _target_city(update.city) if "city" in update.model_fields_set else None
    notes = (
        update.notes.strip() if update.notes is not None and update.notes.strip() else None
    )
    return repository.update_external_lead(
        db,
        lead,
        city=city,
        status=update.status,
        notes=notes,
        fields_set=update.model_fields_set,
    )
