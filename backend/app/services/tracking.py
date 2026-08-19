import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.listing import Listing, MarketStatus
from app.models.tracking import (
    DuplicateReviewStatus,
    EventType,
    ListingEvent,
    ListingSnapshot,
    ListingSourceRecord,
    MatchMethod,
    PossibleDuplicate,
)
from app.repositories import tracking as repository
from app.schemas.listing import ListingObservation
from app.schemas.tracking import DuplicateResolutionAction
from app.services.normalization import canonicalize_url, normalize_address


@dataclass(slots=True)
class IngestionResult:
    listing: Listing
    source_record: ListingSourceRecord
    snapshot: ListingSnapshot
    events: list[ListingEvent]
    match_method: MatchMethod
    possible_duplicate: PossibleDuplicate | None


@dataclass(slots=True)
class FuzzyMatch:
    listing: Listing | None
    confidence: float
    reasons: dict[str, object]


@dataclass(slots=True)
class ReconciliationResult:
    reconciled_count: int
    source_removed_count: int
    listing_removed_count: int


def _text_similarity(left: str | None, right: str | None) -> float | None:
    if not left or not right:
        return None
    return SequenceMatcher(None, left.lower(), right.lower()).ratio()


def _numeric_similarity(left: Decimal | int | None, right: Decimal | int | None) -> float | None:
    if left is None or right is None:
        return None
    left_number = float(left)
    right_number = float(right)
    denominator = max(abs(left_number), abs(right_number), 1.0)
    return max(0.0, 1.0 - abs(left_number - right_number) / denominator)


def _fuzzy_score(
    observation: ListingObservation, listing: Listing
) -> tuple[float, dict[str, object]]:
    observation_address = normalize_address(observation.address)
    signals: list[tuple[str, float, float | None]] = [
        ("address", 0.40, _text_similarity(observation_address, listing.normalized_address)),
        ("title", 0.15, _text_similarity(observation.title, listing.title)),
        ("business_name", 0.10, _text_similarity(observation.business_name, listing.business_name)),
        ("asking_price", 0.15, _numeric_similarity(observation.asking_price, listing.asking_price)),
        ("monthly_rent", 0.10, _numeric_similarity(observation.monthly_rent, listing.monthly_rent)),
        ("size_sqft", 0.10, _numeric_similarity(observation.size_sqft, listing.size_sqft)),
    ]
    available = [(name, weight, value) for name, weight, value in signals if value is not None]
    if not available:
        return 0.0, {"signals": {}}

    total_weight = sum(weight for _, weight, _ in available)
    score = sum(weight * float(value) for _, weight, value in available) / total_weight
    reasons = {
        "signals": {name: round(float(value), 4) for name, _, value in available},
        "weighted_score": round(score, 4),
    }
    return score, reasons


def _best_fuzzy_match(db: Session, observation: ListingObservation) -> FuzzyMatch:
    best = FuzzyMatch(listing=None, confidence=0.0, reasons={"signals": {}})
    for candidate in repository.city_candidates(db, city=observation.city.strip()):
        score, reasons = _fuzzy_score(observation, candidate)
        if score > best.confidence:
            best = FuzzyMatch(listing=candidate, confidence=score, reasons=reasons)
    return best


def _new_listing(observation: ListingObservation, normalized_address: str | None) -> Listing:
    return Listing(
        title=observation.title.strip(),
        business_name=observation.business_name,
        description=observation.description,
        address=observation.address,
        normalized_address=normalized_address,
        city=observation.city.strip(),
        zip=observation.zip,
        lat=observation.lat,
        lng=observation.lng,
        asking_price=observation.asking_price,
        monthly_rent=observation.monthly_rent,
        size_sqft=observation.size_sqft,
        seats=observation.seats,
        parking=observation.parking,
        loading_access=observation.loading_access,
        type1_hood=observation.type1_hood,
        hood_length=observation.hood_length,
        grease_trap=observation.grease_trap,
        walk_in_cooler=observation.walk_in_cooler,
        source=observation.source.strip(),
        source_url=observation.source_url.strip(),
        market_status=observation.market_status,
        first_seen_at=observation.captured_at,
        last_seen_at=observation.captured_at,
    )


def _update_current_listing(
    listing: Listing, observation: ListingObservation, normalized_address: str | None
) -> None:
    update_fields = (
        "title",
        "business_name",
        "description",
        "address",
        "zip",
        "lat",
        "lng",
        "asking_price",
        "monthly_rent",
        "size_sqft",
        "seats",
        "parking",
        "loading_access",
        "type1_hood",
        "hood_length",
        "grease_trap",
        "walk_in_cooler",
    )
    for field_name in update_fields:
        value = getattr(observation, field_name)
        if value is not None:
            setattr(listing, field_name, value)

    if normalized_address is not None:
        listing.normalized_address = normalized_address
    if (
        observation.market_status != MarketStatus.UNKNOWN
        or listing.market_status == MarketStatus.UNKNOWN
    ):
        listing.market_status = observation.market_status
    listing.source = observation.source.strip()
    listing.source_url = observation.source_url.strip()
    listing.last_seen_at = observation.captured_at


def _change_events(
    listing: Listing, observation: ListingObservation, snapshot: ListingSnapshot
) -> list[ListingEvent]:
    events: list[ListingEvent] = []

    def add_event(
        event_type: EventType, old_value: dict[str, object], new_value: dict[str, object]
    ) -> None:
        events.append(
            ListingEvent(
                listing_id=listing.id,
                snapshot_id=snapshot.id,
                event_type=event_type,
                old_value=old_value,
                new_value=new_value,
                detected_at=observation.captured_at,
            )
        )

    if observation.asking_price is not None and listing.asking_price is not None:
        if observation.asking_price < listing.asking_price:
            old_price = listing.asking_price
            drop_percent = (
                (old_price - observation.asking_price) / old_price * 100
                if old_price
                else 0
            )
            add_event(
                EventType.PRICE_DROP,
                {"asking_price": str(old_price)},
                {
                    "asking_price": str(observation.asking_price),
                    "drop_percent": round(float(drop_percent), 2),
                },
            )
        elif observation.asking_price > listing.asking_price:
            add_event(
                EventType.PRICE_INCREASE,
                {"asking_price": str(listing.asking_price)},
                {"asking_price": str(observation.asking_price)},
            )

    if (
        observation.monthly_rent is not None
        and listing.monthly_rent is not None
        and observation.monthly_rent != listing.monthly_rent
    ):
        add_event(
            EventType.RENT_CHANGE,
            {"monthly_rent": str(listing.monthly_rent)},
            {"monthly_rent": str(observation.monthly_rent)},
        )

    old_market_status = listing.market_status
    new_market_status = observation.market_status
    if new_market_status != MarketStatus.UNKNOWN and new_market_status != old_market_status:
        if old_market_status == MarketStatus.OFF_MARKET and new_market_status in {
            MarketStatus.ACTIVE,
            MarketStatus.PENDING,
        }:
            event_type = EventType.BACK_ON_MARKET
        elif new_market_status == MarketStatus.OFF_MARKET:
            event_type = EventType.LISTING_REMOVED
        else:
            event_type = EventType.STATUS_CHANGE
        add_event(
            event_type,
            {"market_status": old_market_status.value},
            {"market_status": new_market_status.value},
        )

    return events


def ingest_observation(db: Session, observation: ListingObservation) -> IngestionResult:
    settings = get_settings()
    canonical_url = canonicalize_url(observation.source_url)
    normalized_address = normalize_address(observation.address)
    source_record = repository.find_source_record(
        db,
        canonical_url=canonical_url,
        source=observation.source.strip(),
        external_id=observation.external_id,
    )

    listing: Listing | None = None
    match_method = MatchMethod.NEW
    possible_duplicate: PossibleDuplicate | None = None
    is_new_listing = False
    review_candidate: FuzzyMatch | None = None

    if source_record is not None:
        listing = db.get(Listing, source_record.listing_id)
        match_method = MatchMethod.CANONICAL_URL
    elif normalized_address is not None:
        listing = repository.find_normalized_address_match(
            db, normalized_address=normalized_address, city=observation.city.strip()
        )
        if listing is not None:
            match_method = MatchMethod.NORMALIZED_ADDRESS

    if listing is None:
        fuzzy_match = _best_fuzzy_match(db, observation)
        if (
            fuzzy_match.listing is not None
            and fuzzy_match.confidence >= settings.dedup_auto_match_threshold
        ):
            listing = fuzzy_match.listing
            match_method = MatchMethod.FUZZY
        elif (
            fuzzy_match.listing is not None
            and fuzzy_match.confidence >= settings.dedup_review_threshold
        ):
            review_candidate = fuzzy_match
            match_method = MatchMethod.REVIEW

    if listing is None:
        listing = _new_listing(observation, normalized_address)
        db.add(listing)
        db.flush()
        is_new_listing = True

    if source_record is None:
        source_record = ListingSourceRecord(
            listing_id=listing.id,
            source=observation.source.strip(),
            external_id=observation.external_id,
            source_url=observation.source_url.strip(),
            canonical_url=canonical_url,
            raw_payload=jsonable_encoder(observation.raw_payload),
            first_seen_at=observation.captured_at,
            last_seen_at=observation.captured_at,
            last_checked_at=observation.captured_at,
            market_status=observation.market_status,
        )
        db.add(source_record)
        db.flush()
    else:
        source_record.source_url = observation.source_url.strip()
        source_record.canonical_url = canonical_url
        source_record.raw_payload = jsonable_encoder(observation.raw_payload)
        source_record.last_seen_at = observation.captured_at
        source_record.last_checked_at = observation.captured_at
        source_record.missed_scan_count = 0
        source_record.removed_at = None
        source_record.market_status = observation.market_status

    snapshot = ListingSnapshot(
        listing_id=listing.id,
        source_record_id=source_record.id,
        asking_price=observation.asking_price,
        monthly_rent=observation.monthly_rent,
        description=observation.description,
        market_status=observation.market_status,
        captured_at=observation.captured_at,
    )
    db.add(snapshot)
    db.flush()

    events: list[ListingEvent] = []
    if is_new_listing and review_candidate is None:
        events.append(
            ListingEvent(
                listing_id=listing.id,
                snapshot_id=snapshot.id,
                event_type=EventType.NEW_LISTING,
                old_value=None,
                new_value={"source": observation.source, "source_url": observation.source_url},
                detected_at=observation.captured_at,
            )
        )
    elif not is_new_listing:
        events.extend(_change_events(listing, observation, snapshot))

    db.add_all(events)

    if review_candidate is not None and review_candidate.listing is not None:
        possible_duplicate = PossibleDuplicate(
            listing_id=listing.id,
            candidate_listing_id=review_candidate.listing.id,
            confidence=review_candidate.confidence,
            match_reasons=review_candidate.reasons,
        )
        db.add(possible_duplicate)

    _update_current_listing(listing, observation, normalized_address)
    db.commit()
    db.refresh(listing)
    db.refresh(snapshot)
    for event in events:
        db.refresh(event)
    if possible_duplicate is not None:
        db.refresh(possible_duplicate)

    return IngestionResult(
        listing=listing,
        source_record=source_record,
        snapshot=snapshot,
        events=events,
        match_method=match_method,
        possible_duplicate=possible_duplicate,
    )


def reconcile_missing_source_records(
    db: Session,
    *,
    source: str,
    observed_source_record_ids: set[uuid.UUID],
    missing_scan_threshold: int,
    checked_at: datetime | None = None,
) -> ReconciliationResult:
    """Reconcile a successful complete source scan against previously seen records.

    A source record is only removed after it is absent from multiple consecutive
    successful scans. The canonical listing is removed only when every source record
    for that listing is sold or off market.
    """

    now = checked_at or datetime.now(UTC)
    source_records = list(
        db.scalars(
            select(ListingSourceRecord).where(
                ListingSourceRecord.source == source,
                ListingSourceRecord.removed_at.is_(None),
            )
        )
    )
    reconciled_count = 0
    source_removed_count = 0
    listing_removed_count = 0

    for source_record in source_records:
        if source_record.id in observed_source_record_ids:
            continue

        reconciled_count += 1
        source_record.last_checked_at = now
        source_record.missed_scan_count += 1
        db.add(source_record)

        if source_record.missed_scan_count < missing_scan_threshold:
            continue

        source_record.market_status = MarketStatus.OFF_MARKET
        source_record.removed_at = now
        source_removed_count += 1
        db.flush()

        listing = db.get(Listing, source_record.listing_id)
        if listing is None or listing.market_status == MarketStatus.OFF_MARKET:
            continue

        available_source = db.scalar(
            select(ListingSourceRecord.id)
            .where(
                ListingSourceRecord.listing_id == listing.id,
                ListingSourceRecord.market_status.not_in(
                    (MarketStatus.OFF_MARKET, MarketStatus.SOLD)
                ),
            )
            .limit(1)
        )
        if available_source is not None:
            continue

        old_market_status = listing.market_status
        listing.market_status = MarketStatus.OFF_MARKET
        snapshot = ListingSnapshot(
            listing_id=listing.id,
            source_record_id=source_record.id,
            asking_price=listing.asking_price,
            monthly_rent=listing.monthly_rent,
            description=listing.description,
            market_status=MarketStatus.OFF_MARKET,
            captured_at=now,
        )
        db.add(snapshot)
        db.flush()
        db.add(
            ListingEvent(
                listing_id=listing.id,
                snapshot_id=snapshot.id,
                event_type=EventType.LISTING_REMOVED,
                old_value={"market_status": old_market_status.value},
                new_value={
                    "market_status": MarketStatus.OFF_MARKET.value,
                    "reason": "absent_from_consecutive_successful_scans",
                    "missing_scan_count": source_record.missed_scan_count,
                },
                detected_at=now,
            )
        )
        listing_removed_count += 1

    db.commit()
    return ReconciliationResult(
        reconciled_count=reconciled_count,
        source_removed_count=source_removed_count,
        listing_removed_count=listing_removed_count,
    )


def resolve_possible_duplicate(
    db: Session, review: PossibleDuplicate, action: DuplicateResolutionAction
) -> PossibleDuplicate:
    if review.status != DuplicateReviewStatus.PENDING:
        raise ValueError("Possible duplicate has already been resolved")

    listing = db.get(Listing, review.listing_id)
    candidate = db.get(Listing, review.candidate_listing_id)
    if listing is None or candidate is None:
        raise ValueError("Listing for duplicate review no longer exists")

    now = datetime.now(UTC)
    if action == DuplicateResolutionAction.MERGE:
        repository.move_tracking_records(
            db, source_listing_id=listing.id, target_listing_id=candidate.id
        )
        merge_fields = (
            "business_name",
            "description",
            "address",
            "normalized_address",
            "zip",
            "lat",
            "lng",
            "asking_price",
            "monthly_rent",
            "size_sqft",
            "seats",
            "parking",
            "loading_access",
            "type1_hood",
            "hood_length",
            "grease_trap",
            "walk_in_cooler",
        )
        for field_name in merge_fields:
            if getattr(candidate, field_name) is None and getattr(listing, field_name) is not None:
                setattr(candidate, field_name, getattr(listing, field_name))
        candidate.last_seen_at = max(candidate.last_seen_at, listing.last_seen_at)
        listing.is_duplicate = True
        listing.merged_into_id = candidate.id
        review.status = DuplicateReviewStatus.MERGED
    else:
        review.status = DuplicateReviewStatus.DISTINCT
        latest_snapshot = db.scalar(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == listing.id)
            .order_by(ListingSnapshot.captured_at.desc())
            .limit(1)
        )
        already_announced = db.scalar(
            select(ListingEvent.id).where(
                ListingEvent.listing_id == listing.id,
                ListingEvent.event_type == EventType.NEW_LISTING,
            )
        )
        if already_announced is None:
            db.add(
                ListingEvent(
                    listing_id=listing.id,
                    snapshot_id=latest_snapshot.id if latest_snapshot else None,
                    event_type=EventType.NEW_LISTING,
                    old_value=None,
                    new_value={"resolved_as": "DISTINCT"},
                    detected_at=now,
                )
            )

    review.resolved_at = now
    db.add_all([listing, candidate, review])
    db.commit()
    db.refresh(review)
    return review
