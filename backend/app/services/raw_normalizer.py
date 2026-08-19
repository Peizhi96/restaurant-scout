import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.listing import MarketStatus
from app.schemas.ingestion import RawListing
from app.schemas.listing import ListingObservation


class NormalizationError(ValueError):
    pass


def _required_text(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if value is None or not str(value).strip():
        raise NormalizationError(f"Missing required field: {field_name}")
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _decimal(
    value: Any, field_name: str, *, allow_negative: bool = False
) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise NormalizationError(f"Invalid numeric value for {field_name}")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    cleaned = str(value).strip().lower().replace("$", "").replace(",", "")
    multiplier = Decimal("1")
    if cleaned.endswith("k"):
        multiplier = Decimal("1000")
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = Decimal("1000000")
        cleaned = cleaned[:-1]
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned):
        raise NormalizationError(f"Invalid numeric value for {field_name}: {value}")
    try:
        result = Decimal(cleaned) * multiplier
    except InvalidOperation as exc:
        raise NormalizationError(f"Invalid numeric value for {field_name}: {value}") from exc
    if result < 0 and not allow_negative:
        raise NormalizationError(f"Negative value is not allowed for {field_name}")
    return result


def _integer(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise NormalizationError(f"Invalid integer value for {field_name}")
    if isinstance(value, int):
        result = value
    else:
        cleaned = str(value).strip().lower().replace(",", "")
        cleaned = re.sub(r"\s*(?:sq\.?\s*ft\.?|sqft|sf|seats?)\s*$", "", cleaned)
        if not re.fullmatch(r"\d+", cleaned):
            raise NormalizationError(f"Invalid integer value for {field_name}: {value}")
        result = int(cleaned)
    if result < 0:
        raise NormalizationError(f"Negative value is not allowed for {field_name}")
    return result


def _float(value: Any, field_name: str, *, allow_negative: bool = False) -> float | None:
    decimal_value = _decimal(value, field_name, allow_negative=allow_negative)
    return float(decimal_value) if decimal_value is not None else None


def _boolean(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"yes", "true", "1", "present", "available", "y"}:
        return True
    if normalized in {"no", "false", "0", "absent", "unavailable", "n"}:
        return False
    return None


def _market_status(value: Any) -> MarketStatus:
    if value is None or value == "":
        return MarketStatus.UNKNOWN
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "active": MarketStatus.ACTIVE,
        "available": MarketStatus.ACTIVE,
        "for_sale": MarketStatus.ACTIVE,
        "pending": MarketStatus.PENDING,
        "under_contract": MarketStatus.PENDING,
        "sold": MarketStatus.SOLD,
        "off_market": MarketStatus.OFF_MARKET,
        "removed": MarketStatus.OFF_MARKET,
        "unavailable": MarketStatus.OFF_MARKET,
    }
    return mapping.get(normalized, MarketStatus.UNKNOWN)


def normalize_raw_listing(raw: RawListing) -> ListingObservation:
    payload = raw.payload
    return ListingObservation(
        title=_required_text(payload, "title"),
        business_name=_optional_text(payload.get("business_name")),
        description=_optional_text(payload.get("description")),
        address=_optional_text(payload.get("address")),
        city=_required_text(payload, "city"),
        zip=_optional_text(payload.get("zip")),
        lat=_float(payload.get("lat"), "lat", allow_negative=True),
        lng=_float(payload.get("lng"), "lng", allow_negative=True),
        asking_price=_decimal(payload.get("asking_price"), "asking_price"),
        monthly_rent=_decimal(payload.get("monthly_rent"), "monthly_rent"),
        size_sqft=_integer(payload.get("size_sqft"), "size_sqft"),
        seats=_integer(payload.get("seats"), "seats"),
        parking=_boolean(payload.get("parking")),
        loading_access=_boolean(payload.get("loading_access")),
        type1_hood=_boolean(payload.get("type1_hood")),
        hood_length=_float(payload.get("hood_length"), "hood_length"),
        grease_trap=_boolean(payload.get("grease_trap")),
        walk_in_cooler=_boolean(payload.get("walk_in_cooler")),
        source=raw.source,
        source_url=raw.source_url,
        external_id=raw.external_id,
        market_status=_market_status(payload.get("market_status")),
        captured_at=raw.collected_at,
        raw_payload=payload,
    )
