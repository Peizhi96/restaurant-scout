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


@lru_cache
def get_settings() -> Settings:
    return Settings()
