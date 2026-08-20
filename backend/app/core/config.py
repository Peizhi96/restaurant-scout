import json
import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _env_float_map(name: str, default: dict[str, float]) -> dict[str, float]:
    value = os.getenv(name)
    if value is None:
        return dict(default)
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    result = {str(key): float(weight) for key, weight in payload.items()}
    if any(weight < 0 for weight in result.values()) or not any(result.values()):
        raise ValueError(f"{name} weights must be non-negative with a positive total")
    return result


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Restaurant Scout API"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://restaurant_scout:restaurant_scout_dev@localhost:5432/restaurant_scout",
        )
    )
    dedup_auto_match_threshold: float = field(
        default_factory=lambda: float(os.getenv("DEDUP_AUTO_MATCH_THRESHOLD", "0.90"))
    )
    dedup_review_threshold: float = field(
        default_factory=lambda: float(os.getenv("DEDUP_REVIEW_THRESHOLD", "0.72"))
    )
    internal_api_key: str | None = field(
        default_factory=lambda: os.getenv("INTERNAL_API_KEY")
    )
    restaurant_realty_enabled: bool = field(
        default_factory=lambda: _env_bool("RESTAURANT_REALTY_ENABLED")
    )
    restaurant_realty_site_url: str = field(
        default_factory=lambda: os.getenv(
            "RESTAURANT_REALTY_SITE_URL", "https://restaurantrealty.com"
        ).rstrip("/")
    )
    restaurant_realty_api_url: str = field(
        default_factory=lambda: os.getenv(
            "RESTAURANT_REALTY_API_URL",
            "https://api.restaurantrealty.verticacrm.com/api/bbcrmapi",
        ).rstrip("/")
    )
    restaurant_realty_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("RESTAURANT_REALTY_TIMEOUT_SECONDS", "20")
        )
    )
    restaurant_realty_request_delay_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("RESTAURANT_REALTY_REQUEST_DELAY_SECONDS", "0.5")
        )
    )
    restaurant_realty_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "RESTAURANT_REALTY_USER_AGENT", "RestaurantScout/0.1"
        )
    )
    restaurant_realty_target_cities: tuple[str, ...] = field(
        default_factory=lambda: _env_csv(
            "RESTAURANT_REALTY_TARGET_CITIES",
            (
                "San Mateo",
                "San Carlos",
                "Redwood City",
                "Palo Alto",
                "Mountain View",
                "Sunnyvale",
            ),
        )
    )
    restaurant_realty_target_counties: tuple[str, ...] = field(
        default_factory=lambda: _env_csv(
            "RESTAURANT_REALTY_TARGET_COUNTIES",
            ("San Mateo County", "Santa Clara County"),
        )
    )
    restaurant_for_sales_enabled: bool = field(
        default_factory=lambda: _env_bool("RESTAURANT_FOR_SALES_ENABLED")
    )
    restaurant_for_sales_site_url: str = field(
        default_factory=lambda: os.getenv(
            "RESTAURANT_FOR_SALES_SITE_URL", "https://restaurantforsales.com"
        ).rstrip("/")
    )
    restaurant_for_sales_timeout_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("RESTAURANT_FOR_SALES_TIMEOUT_SECONDS", "20")
        )
    )
    restaurant_for_sales_request_delay_seconds: float = field(
        default_factory=lambda: float(
            os.getenv("RESTAURANT_FOR_SALES_REQUEST_DELAY_SECONDS", "0.5")
        )
    )
    restaurant_for_sales_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "RESTAURANT_FOR_SALES_USER_AGENT", "RestaurantScout/0.1"
        )
    )
    bizbuysell_enabled: bool = field(
        default_factory=lambda: _env_bool("BIZBUYSELL_ENABLED")
    )
    bizbuysell_data_license_confirmed: bool = field(
        default_factory=lambda: _env_bool("BIZBUYSELL_DATA_LICENSE_CONFIRMED")
    )
    bizbuysell_authorized_feed_url: str | None = field(
        default_factory=lambda: _env_optional("BIZBUYSELL_AUTHORIZED_FEED_URL")
    )
    bizbuysell_authorized_feed_token: str | None = field(
        default_factory=lambda: _env_optional("BIZBUYSELL_AUTHORIZED_FEED_TOKEN")
    )
    bizbuysell_feed_is_complete: bool = field(
        default_factory=lambda: _env_bool("BIZBUYSELL_FEED_IS_COMPLETE")
    )
    bizbuysell_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("BIZBUYSELL_TIMEOUT_SECONDS", "20"))
    )
    bizbuysell_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "BIZBUYSELL_USER_AGENT", "RestaurantScout/0.1"
        )
    )
    loopnet_enabled: bool = field(
        default_factory=lambda: _env_bool("LOOPNET_ENABLED")
    )
    loopnet_data_license_confirmed: bool = field(
        default_factory=lambda: _env_bool("LOOPNET_DATA_LICENSE_CONFIRMED")
    )
    loopnet_authorized_feed_url: str | None = field(
        default_factory=lambda: _env_optional("LOOPNET_AUTHORIZED_FEED_URL")
    )
    loopnet_authorized_feed_token: str | None = field(
        default_factory=lambda: _env_optional("LOOPNET_AUTHORIZED_FEED_TOKEN")
    )
    loopnet_feed_is_complete: bool = field(
        default_factory=lambda: _env_bool("LOOPNET_FEED_IS_COMPLETE")
    )
    loopnet_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("LOOPNET_TIMEOUT_SECONDS", "20"))
    )
    loopnet_user_agent: str = field(
        default_factory=lambda: os.getenv("LOOPNET_USER_AGENT", "RestaurantScout/0.1")
    )
    removal_missing_scan_threshold: int = field(
        default_factory=lambda: max(
            2, int(os.getenv("REMOVAL_MISSING_SCAN_THRESHOLD", "2"))
        )
    )
    scheduler_interval_seconds: float = field(
        default_factory=lambda: max(
            60.0, float(os.getenv("SCHEDULER_INTERVAL_SECONDS", "86400"))
        )
    )
    scheduler_initial_delay_seconds: float = field(
        default_factory=lambda: max(
            0.0, float(os.getenv("SCHEDULER_INITIAL_DELAY_SECONDS", "60"))
        )
    )
    max_preferred_rent: float = field(
        default_factory=lambda: float(os.getenv("MAX_PREFERRED_RENT", "8000"))
    )
    max_preferred_asking_price: float = field(
        default_factory=lambda: float(os.getenv("MAX_PREFERRED_ASKING_PRICE", "300000"))
    )
    min_preferred_sqft: float = field(
        default_factory=lambda: float(os.getenv("MIN_PREFERRED_SQFT", "1200"))
    )
    max_preferred_sqft: float = field(
        default_factory=lambda: float(os.getenv("MAX_PREFERRED_SQFT", "2500"))
    )
    corporate_score_weight: float = field(
        default_factory=lambda: float(os.getenv("CORPORATE_SCORE_WEIGHT", "0.60"))
    )
    restaurant_score_weight: float = field(
        default_factory=lambda: float(os.getenv("RESTAURANT_SCORE_WEIGHT", "0.40"))
    )
    corporate_factor_weights: dict[str, float] = field(
        default_factory=lambda: _env_float_map(
            "CORPORATE_FACTOR_WEIGHTS_JSON",
            {
                "tech_company_delivery_location": 25,
                "kitchen_production_capacity": 20,
                "delivery_logistics": 15,
                "rent_economics": 15,
                "catering_scalability": 10,
                "storage_refrigeration": 5,
                "parking_loading": 5,
                "existing_equipment": 5,
            },
        )
    )
    restaurant_factor_weights: dict[str, float] = field(
        default_factory=lambda: _env_float_map(
            "RESTAURANT_FACTOR_WEIGHTS_JSON",
            {
                "rent_economics": 20,
                "local_customer_demand": 20,
                "parking": 15,
                "competition": 15,
                "visibility": 10,
                "household_purchasing_power": 10,
                "kitchen": 5,
                "seats": 5,
            },
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
