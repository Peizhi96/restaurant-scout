import re
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.base import Collector
from app.schemas.ingestion import RawListing

SOURCE_NAME = "restaurant_realty"


class RestaurantRealtyResponseError(RuntimeError):
    pass


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _money_value(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    cleaned = re.sub(r"^Offered\s+At\s+", "", cleaned, flags=re.IGNORECASE)
    match = re.fullmatch(
        r"\$?\s*(\d[\d,]*(?:\.\d{1,2})?)(?:\s*\([^)]*\))?",
        cleaned,
    )
    return match.group(1).replace(",", "") if match else None


def _whole_number(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    match = re.fullmatch(
        r"([\d,]+)(?:\s*(?:sq\.?\s*ft\.?|sqft|sf|seats?))?",
        cleaned,
        flags=re.IGNORECASE,
    )
    return match.group(1).replace(",", "") if match else None


def _explicit_type1_hood(text: str) -> bool | None:
    hood = r"type\s*(?:1|i)\s+hood"
    if re.search(
        rf"(?:without|no|does\s+not\s+have|not\s+equipped\s+with)\s+(?:a\s+)?{hood}",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    if re.search(hood, text, flags=re.IGNORECASE):
        return True
    return None


def _infer_target_city(
    title: str, description: str | None, target_cities: Sequence[str]
) -> str | None:
    for text in (title, description or ""):
        matches: list[tuple[int, str]] = []
        for city in target_cities:
            for match in re.finditer(
                rf"(?<!\w){re.escape(city)}(?!\w)", text, flags=re.IGNORECASE
            ):
                suffix = text[match.end() :]
                if re.match(r"\s+County\b", suffix, flags=re.IGNORECASE):
                    continue
                matches.append((match.start(), city))
        if matches:
            return min(matches)[1]
    return None


def _response_html(response: httpx.Response, expected_type: str) -> tuple[str, dict[str, Any]]:
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RestaurantRealtyResponseError("Restaurant Realty returned invalid JSON") from exc
    if payload.get("code") != 200 or payload.get("type") != expected_type:
        raise RestaurantRealtyResponseError(
            f"Unexpected Restaurant Realty response: code={payload.get('code')}, "
            f"type={payload.get('type')}"
        )
    body = payload.get("body")
    if not isinstance(body, dict) or not isinstance(body.get("html"), str):
        raise RestaurantRealtyResponseError("Restaurant Realty response has no HTML body")
    return body["html"], body


def parse_listing_ids(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    listing_ids: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("#bbcrm-listings-searchresults a[href*='listing=']"):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        match = re.search(r"[?&]listing=(\d+)", href)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            listing_ids.append(match.group(1))
    return listing_ids


def _detail_pairs(soup: BeautifulSoup) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for block in soup.select(".datablock"):
        label = block.select_one(".datahead")
        value = block.select_one(".datainfo")
        if label is not None and value is not None:
            key = _clean_text(label.get_text(" ", strip=True))
            if key:
                pairs[key.casefold()] = _clean_text(value.get_text(" ", strip=True)) or ""
    for label in soup.select(".detailblock .detaillable"):
        value = label.find_next_sibling("div", class_="detailinfo")
        if isinstance(value, Tag):
            key = _clean_text(label.get_text(" ", strip=True))
            if key:
                pairs[key.casefold()] = _clean_text(value.get_text(" ", strip=True)) or ""
    return pairs


def parse_listing_detail(
    html: str,
    *,
    external_id: str,
    target_cities: Sequence[str],
) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("#maintitle")
    if title_node is None:
        raise RestaurantRealtyResponseError(
            f"Restaurant Realty listing {external_id} has no title"
        )
    title = _clean_text(title_node.get_text(" ", strip=True))
    if title is None:
        raise RestaurantRealtyResponseError(
            f"Restaurant Realty listing {external_id} has an empty title"
        )

    description_node = soup.select_one("#maindesc")
    description = (
        _clean_text(description_node.get_text("\n", strip=True))
        if description_node is not None
        else None
    )
    city = _infer_target_city(title, description, target_cities)
    if city is None:
        return None

    pairs = _detail_pairs(soup)
    offer_node = next(
        (
            node
            for node in soup.select(".soldremove")
            if _clean_text(node.get_text(" ", strip=True) or "").lower().startswith(
                "offered at"
            )
        ),
        None,
    )
    offer_text = offer_node.get_text(" ", strip=True) if offer_node is not None else None
    parking_text = pairs.get("parking") or None
    combined_text = " ".join(item for item in (title, description) if item)

    return {
        "title": title,
        "description": description,
        "city": city,
        "asking_price": _money_value(offer_text),
        "monthly_rent": _money_value(pairs.get("rent")),
        "size_sqft": _whole_number(pairs.get("square feet") or pairs.get("sq ft")),
        "seats": _whole_number(pairs.get("seating")),
        "parking": None,
        "parking_text": parking_text,
        "type1_hood": _explicit_type1_hood(combined_text),
        "property_types": pairs.get("type") or None,
        "lease_expiration": pairs.get("expiration") or None,
        "lease_option": pairs.get("option") or None,
        "market_status": "active",
    }


class RestaurantRealtyCollector(Collector):
    supports_reconciliation = True

    def __init__(
        self,
        *,
        site_url: str,
        api_url: str,
        target_cities: Sequence[str],
        target_counties: Sequence[str],
        timeout_seconds: float = 20,
        request_delay_seconds: float = 0.5,
        user_agent: str = "RestaurantScout/0.1",
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.site_url = site_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self.target_cities = tuple(target_cities)
        self.target_counties = tuple(target_counties)
        self.request_delay_seconds = max(0, request_delay_seconds)
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            transport=httpx.HTTPTransport(retries=2),
        )
        self._headers = {
            "Origin": self.site_url,
            "Referer": f"{self.site_url}/",
            "User-Agent": user_agent,
            "X-Requested-With": "XMLHttpRequest",
        }

    @property
    def name(self) -> str:
        return SOURCE_NAME

    def _post(self, endpoint: str, data: dict[str, str]) -> httpx.Response:
        return self._client.post(
            f"{self.api_url}/{endpoint}",
            headers=self._headers,
            data=data,
        )

    def _listing_ids(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        search_url = f"{self.site_url}/search-listing-by-list/"
        for index, county in enumerate(self.target_counties):
            if index:
                self._sleep(self.request_delay_seconds)
            response = self._post(
                "submitsearchtoolnew",
                {
                    "authorization": "",
                    "url": search_url,
                    "language": "",
                    "lazyload": "1",
                    "template": "listviewnew.html",
                    "sort": "id:desc",
                    "presets": (
                        "c_sales_stage:=:Active, c_webdisplay:!=:Sold, "
                        "c_webdisplay:!=:Leased"
                    ),
                    "search": (
                        f"c_County={county}&pagenumber=1&resultsperpage=100"
                    ),
                },
            )
            html, _ = _response_html(response, "listings")
            for listing_id in parse_listing_ids(html):
                if listing_id not in seen:
                    seen.add(listing_id)
                    result.append(listing_id)
        return result

    def collect(self) -> Iterable[RawListing]:
        try:
            for listing_id in self._listing_ids():
                self._sleep(self.request_delay_seconds)
                source_url = f"{self.site_url}/listing/?listing={listing_id}"
                response = self._post(
                    "listing",
                    {
                        "authorization": "",
                        "url": source_url,
                        "language": "",
                        "jsTree": "1",
                    },
                )
                html, body = _response_html(response, "listings")
                payload = parse_listing_detail(
                    html,
                    external_id=str(body.get("listing_id") or listing_id),
                    target_cities=self.target_cities,
                )
                if payload is None:
                    continue
                yield RawListing(
                    source=SOURCE_NAME,
                    source_url=source_url,
                    external_id=listing_id,
                    payload=payload,
                    collected_at=datetime.now(UTC),
                )
        finally:
            if self._owns_client:
                self._client.close()
