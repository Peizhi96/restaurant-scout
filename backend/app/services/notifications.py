import logging
import smtplib
import ssl
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.ingestion import CollectionRun, RawListingRecord
from app.models.intelligence import (
    EmailNotification,
    NotificationPriority,
    NotificationStatus,
)
from app.models.listing import Listing
from app.models.tracking import EventType, ListingEvent

logger = logging.getLogger(__name__)


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SMTPTransport:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        settings = self.settings
        connection_type = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with connection_type(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)


def _event_drop_percent(event: ListingEvent) -> Decimal | None:
    value = (event.new_value or {}).get("drop_percent")
    try:
        return Decimal(str(value)) if value is not None else None
    except InvalidOperation:
        return None


def _notification_reason(
    listing: Listing, event: ListingEvent, settings: Settings
) -> tuple[str, NotificationPriority] | None:
    score = Decimal(listing.overall_score) if listing.overall_score is not None else None
    if event.event_type == EventType.NEW_LISTING:
        if score is not None and score >= Decimal(str(settings.alert_high_score_threshold)):
            return None
        if score is not None and score >= Decimal(str(settings.alert_new_score_threshold)):
            return "NEW_HIGH_SCORE", NotificationPriority.NORMAL
        return None
    if event.event_type == EventType.PRICE_DROP:
        drop = _event_drop_percent(event)
        if drop is not None and drop >= Decimal(str(settings.alert_price_drop_percent)):
            return "PRICE_DROP", NotificationPriority.HIGH
    if listing.status.value in settings.alert_watched_statuses:
        return "WATCHED_CHANGE", NotificationPriority.NORMAL
    return None


def _build_body(
    listing: Listing, event: ListingEvent | None, trigger: str
) -> str:
    score = f"{listing.overall_score}/100" if listing.overall_score is not None else "UNKNOWN"
    asking_price = listing.asking_price if listing.asking_price is not None else "UNKNOWN"
    monthly_rent = listing.monthly_rent if listing.monthly_rent is not None else "UNKNOWN"
    return "\n".join(
        (
            f"Trigger: {trigger}",
            f"Listing: {listing.title}",
            f"City: {listing.city}",
            f"Overall score: {score}",
            f"Event: {event.event_type.value if event else 'SCORE_THRESHOLD'}",
            f"Asking price: {asking_price}",
            f"Monthly rent: {monthly_rent}",
            f"Source: {listing.source_url}",
            "",
            "Unknown facts remain UNKNOWN and are not treated as zero.",
        )
    )


def queue_event_notification(
    db: Session,
    listing: Listing,
    event: ListingEvent,
    *,
    settings: Settings | None = None,
) -> EmailNotification | None:
    settings = settings or get_settings()
    if not settings.alert_recipient:
        return None
    db.refresh(listing, attribute_names=["score"])
    reason = _notification_reason(listing, event, settings)
    if reason is None:
        return None
    trigger, priority = reason
    deduplication_key = f"{settings.alert_recipient}:{trigger}:{event.id}"
    existing = db.scalar(
        select(EmailNotification).where(
            EmailNotification.deduplication_key == deduplication_key
        )
    )
    if existing is not None:
        return existing
    prefix = "[HIGH] " if priority == NotificationPriority.HIGH else ""
    notification = EmailNotification(
        listing_id=listing.id,
        event_id=event.id,
        trigger_type=trigger,
        priority=priority,
        recipient=settings.alert_recipient,
        subject=f"{prefix}Restaurant Scout: {listing.title}",
        body_text=_build_body(listing, event, trigger),
        deduplication_key=deduplication_key,
    )
    db.add(notification)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(
            select(EmailNotification).where(
                EmailNotification.deduplication_key == deduplication_key
            )
        )
    db.refresh(notification)
    return notification


def queue_high_score_notification(
    db: Session,
    listing: Listing,
    *,
    settings: Settings | None = None,
) -> EmailNotification | None:
    settings = settings or get_settings()
    if not settings.alert_recipient:
        return None
    db.refresh(listing, attribute_names=["score"])
    score = Decimal(listing.overall_score) if listing.overall_score is not None else None
    if score is None or score < Decimal(str(settings.alert_high_score_threshold)):
        return None
    deduplication_key = f"{settings.alert_recipient}:HIGH_SCORE:{listing.id}"
    existing = db.scalar(
        select(EmailNotification).where(
            EmailNotification.deduplication_key == deduplication_key
        )
    )
    if existing is not None:
        return existing
    notification = EmailNotification(
        listing_id=listing.id,
        event_id=None,
        trigger_type="HIGH_SCORE",
        priority=NotificationPriority.HIGH,
        recipient=settings.alert_recipient,
        subject=f"[HIGH] Restaurant Scout: {listing.title}",
        body_text=_build_body(listing, None, "HIGH_SCORE"),
        deduplication_key=deduplication_key,
    )
    db.add(notification)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(
            select(EmailNotification).where(
                EmailNotification.deduplication_key == deduplication_key
            )
        )
    db.refresh(notification)
    return notification


def deliver_notification(
    db: Session,
    notification: EmailNotification,
    *,
    settings: Settings | None = None,
    transport: EmailTransport | None = None,
) -> EmailNotification:
    settings = settings or get_settings()
    if notification.status == NotificationStatus.SENT:
        return notification
    if not settings.email_enabled and transport is None:
        raise RuntimeError("Email notifications are disabled")
    if not settings.alert_from_email:
        raise RuntimeError("ALERT_FROM_EMAIL is not configured")
    message = EmailMessage()
    message["From"] = settings.alert_from_email
    message["To"] = notification.recipient
    message["Subject"] = notification.subject
    message.set_content(notification.body_text)
    try:
        (transport or SMTPTransport(settings)).send(message)
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        notification.error_message = None
    except Exception as exc:
        notification.status = NotificationStatus.FAILED
        notification.error_message = str(exc)[:4000]
        db.add(notification)
        db.commit()
        raise
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def process_collection_run(
    db: Session,
    run: CollectionRun,
    *,
    settings: Settings | None = None,
    transport: EmailTransport | None = None,
) -> tuple[int, int]:
    settings = settings or get_settings()
    listing_ids = set(
        db.scalars(
            select(RawListingRecord.listing_id).where(
                RawListingRecord.run_id == run.id,
                RawListingRecord.listing_id.is_not(None),
            )
        )
    )
    if not listing_ids:
        return 0, 0
    events = list(
        db.scalars(
            select(ListingEvent).where(
                ListingEvent.listing_id.in_(listing_ids),
            )
        )
    )
    queued = 0
    sent = 0
    for listing_id in listing_ids:
        if listing_id is None:
            continue
        listing = db.get(Listing, listing_id)
        if listing is None:
            continue
        notification = queue_high_score_notification(db, listing, settings=settings)
        if notification is None:
            continue
        queued += 1
        if settings.email_enabled or transport is not None:
            try:
                deliver_notification(
                    db, notification, settings=settings, transport=transport
                )
                sent += 1
            except Exception:
                logger.exception("Email delivery failed for notification %s", notification.id)
    for event in events:
        listing = db.get(Listing, event.listing_id)
        if listing is None:
            continue
        notification = queue_event_notification(db, listing, event, settings=settings)
        if notification is None:
            continue
        queued += 1
        if settings.email_enabled or transport is not None:
            try:
                deliver_notification(
                    db, notification, settings=settings, transport=transport
                )
                sent += 1
            except Exception:
                logger.exception("Email delivery failed for notification %s", notification.id)
    return queued, sent


def listing_ids_for_run(db: Session, run_id: uuid.UUID) -> set[uuid.UUID]:
    return {
        listing_id
        for listing_id in db.scalars(
            select(RawListingRecord.listing_id).where(
                RawListingRecord.run_id == run_id,
                RawListingRecord.listing_id.is_not(None),
            )
        )
        if listing_id is not None
    }
