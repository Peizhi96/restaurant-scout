import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.listing import Listing
from app.models.scoring import ListingScore


@dataclass(frozen=True, slots=True)
class Signal:
    score: float | None
    missing: tuple[str, ...] = ()
    evidence: dict[str, Any] | None = None


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _boolean_signal(value: bool | None, field_name: str) -> Signal:
    if value is None:
        return Signal(None, (field_name,))
    return Signal(100.0 if value else 0.0, evidence={field_name: value})


def _combine(signals: list[tuple[float, Signal]]) -> Signal:
    available = [(weight, signal) for weight, signal in signals if signal.score is not None]
    missing = tuple(
        dict.fromkeys(item for _, signal in signals for item in signal.missing)
    )
    if not available:
        return Signal(None, missing)
    total = sum(weight for weight, _ in available)
    score = sum(weight * float(signal.score) for weight, signal in available) / total
    evidence: dict[str, Any] = {}
    for _, signal in available:
        evidence.update(signal.evidence or {})
    return Signal(_clamp(score), missing, evidence)


def _rent_signal(listing: Listing, settings: Settings) -> Signal:
    if listing.monthly_rent is None:
        return Signal(None, ("monthly_rent",))
    rent = float(listing.monthly_rent)
    preferred = max(1.0, settings.max_preferred_rent)
    absolute = _clamp(100 - max(0.0, rent - preferred) / preferred * 100)
    evidence: dict[str, Any] = {"monthly_rent": rent}
    signals = [(0.7, Signal(absolute, evidence=evidence))]
    if listing.size_sqft:
        rent_psf = rent / listing.size_sqft
        evidence["rent_per_sqft_month"] = round(rent_psf, 2)
        psf_score = _clamp(100 - max(0.0, rent_psf - 5.0) / 5.0 * 100)
        signals.append((0.3, Signal(psf_score, evidence=evidence)))
    return _combine(signals)


def _size_signal(listing: Listing, settings: Settings) -> Signal:
    if listing.size_sqft is None:
        return Signal(None, ("size_sqft",))
    size = float(listing.size_sqft)
    minimum = max(1.0, settings.min_preferred_sqft)
    maximum = max(minimum, settings.max_preferred_sqft)
    if minimum <= size <= maximum:
        score = 100.0
    elif size < minimum:
        score = size / minimum * 100
    else:
        score = max(0.0, 100 - (size - maximum) / maximum * 100)
    return Signal(_clamp(score), evidence={"size_sqft": int(size)})


def _seats_signal(listing: Listing) -> Signal:
    if listing.seats is None:
        return Signal(None, ("seats",))
    if listing.seats >= 60:
        score = 100.0
    elif listing.seats >= 30:
        score = 75.0
    elif listing.seats > 0:
        score = 50.0
    else:
        score = 0.0
    return Signal(score, evidence={"seats": listing.seats})


def _location_signal(listing: Listing, settings: Settings) -> Signal:
    target = {city.casefold() for city in settings.restaurant_realty_target_cities}
    in_corridor = listing.city.casefold() in target
    return Signal(
        100.0 if in_corridor else 40.0,
        evidence={"city": listing.city, "in_target_corridor": in_corridor},
    )


def _factor(
    name: str, weight: float, signal: Signal
) -> tuple[str, dict[str, Any]]:
    return (
        name,
        {
            "weight": weight,
            "score": round(signal.score, 2) if signal.score is not None else None,
            "weighted_points": (
                round(weight * signal.score / 100, 2)
                if signal.score is not None
                else None
            ),
            "available": signal.score is not None,
            "evidence": signal.evidence or {},
            "missing": list(signal.missing),
        },
    )


def _score_factors(
    weights: dict[str, float], signals: dict[str, Signal]
) -> tuple[float | None, float, dict[str, Any], list[str]]:
    factors = dict(
        _factor(name, weight, signals.get(name, Signal(None, (name,))))
        for name, weight in weights.items()
    )
    total_weight = sum(weights.values())
    available_weight = sum(
        weights[name] for name, detail in factors.items() if detail["available"]
    )
    if available_weight:
        earned = sum(
            float(detail["weighted_points"] or 0)
            for detail in factors.values()
            if detail["available"]
        )
        score = earned / available_weight * 100
    else:
        score = None
    completeness = available_weight / total_weight * 100 if total_weight else 0.0
    missing = list(
        dict.fromkeys(
            item
            for detail in factors.values()
            for item in detail["missing"]
        )
    )
    return (
        round(score, 2) if score is not None else None,
        round(completeness, 2),
        factors,
        missing,
    )


def calculate_scores(
    listing: Listing, settings: Settings | None = None
) -> dict[str, Any]:
    settings = settings or get_settings()
    kitchen = _combine(
        [
            (0.6, _boolean_signal(listing.type1_hood, "type1_hood")),
            (0.2, _boolean_signal(listing.grease_trap, "grease_trap")),
            (0.2, _boolean_signal(listing.walk_in_cooler, "walk_in_cooler")),
        ]
    )
    logistics = _combine(
        [
            (0.65, _boolean_signal(listing.loading_access, "loading_access")),
            (0.35, _boolean_signal(listing.parking, "parking")),
        ]
    )
    parking_loading = _combine(
        [
            (0.5, _boolean_signal(listing.parking, "parking")),
            (0.5, _boolean_signal(listing.loading_access, "loading_access")),
        ]
    )
    existing_equipment = _combine(
        [
            (0.7, _boolean_signal(listing.type1_hood, "type1_hood")),
            (0.3, _boolean_signal(listing.grease_trap, "grease_trap")),
        ]
    )

    corporate_signals = {
        "tech_company_delivery_location": _location_signal(listing, settings),
        "kitchen_production_capacity": kitchen,
        "delivery_logistics": logistics,
        "rent_economics": _rent_signal(listing, settings),
        "catering_scalability": _size_signal(listing, settings),
        "storage_refrigeration": _boolean_signal(
            listing.walk_in_cooler, "walk_in_cooler"
        ),
        "parking_loading": parking_loading,
        "existing_equipment": existing_equipment,
    }
    restaurant_signals = {
        "rent_economics": _rent_signal(listing, settings),
        "local_customer_demand": Signal(None, ("local_customer_demand_data",)),
        "parking": _boolean_signal(listing.parking, "parking"),
        "competition": Signal(None, ("competition_data",)),
        "visibility": Signal(None, ("visibility_data",)),
        "household_purchasing_power": Signal(
            None, ("household_purchasing_power_data",)
        ),
        "kitchen": kitchen,
        "seats": _seats_signal(listing),
    }
    corporate, corporate_complete, corporate_factors, corporate_missing = _score_factors(
        settings.corporate_factor_weights, corporate_signals
    )
    restaurant, restaurant_complete, restaurant_factors, restaurant_missing = _score_factors(
        settings.restaurant_factor_weights, restaurant_signals
    )

    overall = None
    if corporate is not None and restaurant is not None:
        total = settings.corporate_score_weight + settings.restaurant_score_weight
        overall = round(
            (
                settings.corporate_score_weight * corporate
                + settings.restaurant_score_weight * restaurant
            )
            / total,
            2,
        )

    return {
        "corporate_catering_score": corporate,
        "restaurant_score": restaurant,
        "overall_score": overall,
        "corporate_completeness": corporate_complete,
        "restaurant_completeness": restaurant_complete,
        "corporate_factors": corporate_factors,
        "restaurant_factors": restaurant_factors,
        "missing_information": list(
            dict.fromkeys(corporate_missing + restaurant_missing)
        ),
    }


def score_listing(db: Session, listing: Listing) -> ListingScore:
    result = calculate_scores(listing)
    score = db.get(ListingScore, listing.id) or ListingScore(listing_id=listing.id)
    for name in (
        "corporate_catering_score",
        "restaurant_score",
        "overall_score",
        "corporate_completeness",
        "restaurant_completeness",
    ):
        value = result[name]
        setattr(score, name, Decimal(f"{value:.2f}") if value is not None else None)
    score.corporate_factors = result["corporate_factors"]
    score.restaurant_factors = result["restaurant_factors"]
    score.missing_information = result["missing_information"]
    score.config_version = "v1-default"
    score.calculated_at = datetime.now(UTC)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_or_calculate_score(db: Session, listing_id: uuid.UUID) -> ListingScore | None:
    listing = db.get(Listing, listing_id)
    if listing is None:
        return None
    return score_listing(db, listing)
