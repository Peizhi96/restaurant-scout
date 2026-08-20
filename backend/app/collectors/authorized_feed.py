from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.collectors.base import Collector
from app.schemas.ingestion import RawListing


class AuthorizedFeedError(RuntimeError):
    pass


def _required_text(item: dict[str, Any], field_name: str) -> str:
    value = item.get(field_name)
    if value is None or not str(value).strip():
        raise AuthorizedFeedError(f"Authorized feed item is missing {field_name}")
    return str(value).strip()


def _collected_at(value: Any) -> datetime:
    if value is None or value == "":
        return datetime.now(UTC)
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise AuthorizedFeedError(
                f"Invalid collected_at value in authorized feed: {value}"
            ) from exc
    if result.tzinfo is None:
        return result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _food_service_payload(payload: dict[str, Any]) -> bool:
    fields = (
        "title",
        "description",
        "category",
        "business_type",
        "property_type",
        "property_types",
        "listing_type",
    )
    text = " ".join(str(payload[name]) for name in fields if payload.get(name))
    if re.search(
        r"\b(?:beauty|nail|hair)\s+salon\b|\bpreschool\b|\bdaycare\b|"
        r"\bauto\s+body\b|\bdry\s+clean(?:er|ing)?\b|\bliquor\s+store\b|"
        r"\btrading\s+card\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(
        re.search(
            r"\b(?:restaurant|cafe|coffee|tea|boba|bakery|dessert|beverage|food|"
            r"kitchen|bar|sushi|pizza|taco|sandwich|noodle|ramen|deli|juice|"
            r"smoothie|second[- ]generation restaurant)\b|café",
            text,
            flags=re.IGNORECASE,
        )
    )


class AuthorizedJsonFeedCollector(Collector):
    """Collect listings from an explicitly licensed, operator-configured JSON feed.

    This adapter deliberately performs one request to the configured feed URL. It does
    not discover, crawl, or open source-site pages. The feed contract is either a JSON
    list or ``{"items": [...]}``; every item contains ``external_id``, ``source_url``,
    and a normalized ``payload`` object suitable for Restaurant Scout ingestion.
    """

    def __init__(
        self,
        *,
        source_name: str,
        feed_url: str,
        allowed_listing_hosts: Sequence[str],
        target_cities: Sequence[str],
        feed_is_complete: bool = False,
        bearer_token: str | None = None,
        timeout_seconds: float = 20,
        user_agent: str = "RestaurantScout/0.1",
        client: httpx.Client | None = None,
    ) -> None:
        parsed_feed_url = urlparse(feed_url)
        if parsed_feed_url.scheme not in {"http", "https"} or not parsed_feed_url.netloc:
            raise ValueError("Authorized feed URL must be an absolute HTTP(S) URL")
        self._source_name = source_name
        self.feed_url = feed_url
        self.allowed_listing_hosts = tuple(host.casefold() for host in allowed_listing_hosts)
        self.target_cities = {
            city.casefold(): city for city in target_cities if city.strip()
        }
        self.supports_reconciliation = feed_is_complete
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=2),
        )
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        if bearer_token:
            self._headers["Authorization"] = f"Bearer {bearer_token}"

    @property
    def name(self) -> str:
        return self._source_name

    def _items(self, response: httpx.Response) -> list[dict[str, Any]]:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").casefold()
        if "json" not in content_type:
            raise AuthorizedFeedError("Authorized feed did not return JSON")
        try:
            document = response.json()
        except ValueError as exc:
            raise AuthorizedFeedError("Authorized feed returned invalid JSON") from exc
        raw_items = document.get("items") if isinstance(document, dict) else document
        if not isinstance(raw_items, list):
            raise AuthorizedFeedError(
                'Authorized feed must be a JSON list or an object with an "items" list'
            )
        if not all(isinstance(item, dict) for item in raw_items):
            raise AuthorizedFeedError("Every authorized feed item must be a JSON object")
        return raw_items

    def _listing_host_allowed(self, source_url: str) -> bool:
        hostname = (urlparse(source_url).hostname or "").casefold()
        return any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in self.allowed_listing_hosts
        )

    def collect(self) -> Iterable[RawListing]:
        try:
            response = self._client.get(self.feed_url, headers=self._headers)
            seen: set[str] = set()
            for item in self._items(response):
                external_id = _required_text(item, "external_id")
                if external_id in seen:
                    continue
                source_url = _required_text(item, "source_url")
                if not self._listing_host_allowed(source_url):
                    raise AuthorizedFeedError(
                        f"Listing URL host is not valid for {self.name}: {source_url}"
                    )
                payload = item.get("payload")
                if not isinstance(payload, dict):
                    raise AuthorizedFeedError(
                        f"Authorized feed item {external_id} has no payload object"
                    )
                if not _food_service_payload(payload):
                    continue
                city = payload.get("city")
                canonical_city = (
                    self.target_cities.get(str(city).strip().casefold())
                    if city is not None
                    else None
                )
                if canonical_city is None:
                    continue
                payload = dict(payload)
                payload["city"] = canonical_city
                seen.add(external_id)
                yield RawListing(
                    source=self.name,
                    source_url=source_url,
                    external_id=external_id,
                    payload=payload,
                    collected_at=_collected_at(item.get("collected_at")),
                )
        finally:
            if self._owns_client:
                self._client.close()
