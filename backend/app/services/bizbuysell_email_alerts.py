from __future__ import annotations

import html
import imaplib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.external_lead import (
    ExternalLeadDiscoveryMethod,
    ExternalLeadSource,
    ExternalLeadSyncRun,
    ExternalLeadSyncStatus,
)
from app.repositories import external_leads as repository
from app.services import external_leads

_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class EmailAlertSyncDisabledError(RuntimeError):
    pass


class EmailAlertSyncError(RuntimeError):
    pass


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        for name, value in attrs:
            if name.casefold() == "href" and value:
                self.hrefs.append(value)


@dataclass(frozen=True, slots=True)
class EmailAlertExtraction:
    sender: str
    urls: tuple[str, ...]
    city: str | None


def _sender_allowed(sender: str, allowed_domains: Sequence[str]) -> bool:
    address = parseaddr(sender)[1].casefold()
    domain = address.rpartition("@")[2]
    return bool(domain) and any(
        domain == allowed.casefold() or domain.endswith(f".{allowed.casefold()}")
        for allowed in allowed_domains
    )


def _message_text(message: EmailMessage) -> tuple[list[str], str]:
    url_candidates: list[str] = []
    visible_parts: list[str] = []
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue
        try:
            content = part.get_content()
        except (LookupError, UnicodeError):
            continue
        if not isinstance(content, str):
            continue
        visible_parts.append(content)
        url_candidates.extend(_URL_PATTERN.findall(content))
        if part.get_content_type() == "text/html":
            parser = _HrefParser()
            parser.feed(content)
            url_candidates.extend(parser.hrefs)
    return url_candidates, " ".join(visible_parts)


def _nested_url_candidates(value: str) -> list[str]:
    queue = [html.unescape(value).strip().rstrip(".,);]")]
    found: list[str] = []
    seen: set[str] = set()
    while queue and len(seen) < 20:
        candidate = queue.pop(0)
        if candidate in seen:
            continue
        seen.add(candidate)
        found.append(candidate)
        parsed = urlsplit(candidate)
        for _, nested in parse_qsl(parsed.query, keep_blank_values=False):
            decoded = unquote(html.unescape(nested)).strip()
            if decoded.casefold().startswith(("http://", "https://")):
                queue.append(decoded)
    return found


def _bizbuysell_urls(candidates: Sequence[str]) -> tuple[str, ...]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        for candidate in _nested_url_candidates(raw):
            try:
                source_url, canonical_url, source = (
                    external_leads.canonicalize_external_lead_url(candidate)
                )
            except external_leads.ExternalLeadUrlError:
                continue
            if source != ExternalLeadSource.BIZBUYSELL or canonical_url in seen:
                continue
            seen.add(canonical_url)
            urls.append(source_url)
    return tuple(urls)


def _single_target_city(text: str, target_cities: Sequence[str]) -> str | None:
    matched: list[str] = []
    for city in target_cities:
        for match in re.finditer(
            rf"(?<!\w){re.escape(city)}(?!\w)", text, flags=re.IGNORECASE
        ):
            if re.match(r"\s+County\b", text[match.end() :], flags=re.IGNORECASE):
                continue
            matched.append(city)
            break
    unique = list(dict.fromkeys(matched))
    return unique[0] if len(unique) == 1 else None


def extract_email_alert(
    raw_message: bytes,
    *,
    allowed_sender_domains: Sequence[str],
    target_cities: Sequence[str],
) -> EmailAlertExtraction | None:
    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    sender = str(message.get("From", ""))
    if not _sender_allowed(sender, allowed_sender_domains):
        return None
    candidates, body_text = _message_text(message)
    urls = _bizbuysell_urls(candidates)
    searchable_text = " ".join(
        (str(message.get("Subject", "")), body_text)
    )
    return EmailAlertExtraction(
        sender=parseaddr(sender)[1],
        urls=urls,
        city=_single_target_city(searchable_text, target_cities),
    )


def email_alerts_configured(settings: Settings) -> bool:
    return bool(
        settings.bizbuysell_imap_host
        and settings.bizbuysell_imap_username
        and settings.bizbuysell_imap_password
        and settings.bizbuysell_email_allowed_sender_domains
    )


def sync_status(db: Session, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "enabled": settings.bizbuysell_email_alerts_enabled,
        "configured": email_alerts_configured(settings),
        "latest_run": repository.latest_sync_run(db, ExternalLeadSource.BIZBUYSELL),
    }


def _message_bytes(fetch_data: Sequence[Any]) -> bytes | None:
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
            return item[1]
    return None


def sync_email_alerts(
    db: Session,
    *,
    settings: Settings | None = None,
    mailbox_factory: Callable[..., imaplib.IMAP4_SSL] = imaplib.IMAP4_SSL,
) -> ExternalLeadSyncRun:
    settings = settings or get_settings()
    if not settings.bizbuysell_email_alerts_enabled:
        raise EmailAlertSyncDisabledError(
            "BizBuySell email-alert sync is disabled; configure the IMAP settings first"
        )
    if not email_alerts_configured(settings):
        raise EmailAlertSyncDisabledError(
            "BizBuySell email-alert sync is enabled but IMAP settings are incomplete"
        )

    run = repository.create_sync_run(
        db,
        ExternalLeadSyncRun(
            source=ExternalLeadSource.BIZBUYSELL,
            status=ExternalLeadSyncStatus.RUNNING,
        ),
    )
    messages_scanned = 0
    links_found = 0
    leads_created = 0
    leads_existing = 0
    try:
        with mailbox_factory(
            settings.bizbuysell_imap_host,
            settings.bizbuysell_imap_port,
            timeout=30,
        ) as mailbox:
            mailbox.login(
                settings.bizbuysell_imap_username,
                settings.bizbuysell_imap_password,
            )
            status, _ = mailbox.select(settings.bizbuysell_imap_mailbox, readonly=False)
            if status != "OK":
                raise EmailAlertSyncError("The configured IMAP mailbox could not be selected")
            status, payload = mailbox.uid("search", None, "UNSEEN")
            if status != "OK":
                raise EmailAlertSyncError("The configured IMAP mailbox could not be searched")
            message_ids = payload[0].split() if payload and payload[0] else []
            message_ids = message_ids[-settings.bizbuysell_email_sync_max_messages :]
            for message_id in message_ids:
                status, fetch_data = mailbox.uid("fetch", message_id, "(RFC822)")
                if status != "OK":
                    continue
                raw_message = _message_bytes(fetch_data)
                if raw_message is None or len(raw_message) > settings.bizbuysell_email_max_bytes:
                    continue
                extraction = extract_email_alert(
                    raw_message,
                    allowed_sender_domains=settings.bizbuysell_email_allowed_sender_domains,
                    target_cities=settings.restaurant_realty_target_cities,
                )
                if extraction is None:
                    continue
                messages_scanned += 1
                links_found += len(extraction.urls)
                for source_url in extraction.urls:
                    _, created = external_leads.add_external_lead_url(
                        db,
                        source_url=source_url,
                        city=extraction.city,
                        notes=None,
                        discovery_method=ExternalLeadDiscoveryMethod.EMAIL_ALERT,
                    )
                    if created:
                        leads_created += 1
                    else:
                        leads_existing += 1
                mailbox.uid("store", message_id, "+FLAGS", "(\\Seen)")
        return repository.finish_sync_run(
            db,
            run,
            status=ExternalLeadSyncStatus.SUCCEEDED,
            messages_scanned=messages_scanned,
            links_found=links_found,
            leads_created=leads_created,
            leads_existing=leads_existing,
        )
    except EmailAlertSyncDisabledError:
        raise
    except Exception as exc:
        repository.finish_sync_run(
            db,
            run,
            status=ExternalLeadSyncStatus.FAILED,
            messages_scanned=messages_scanned,
            links_found=links_found,
            leads_created=leads_created,
            leads_existing=leads_existing,
            error_message="Mailbox authentication, connection, or message processing failed",
        )
        if isinstance(exc, EmailAlertSyncError):
            raise
        raise EmailAlertSyncError(
            "BizBuySell email-alert sync failed; verify the IMAP connection and mailbox settings"
        ) from exc
