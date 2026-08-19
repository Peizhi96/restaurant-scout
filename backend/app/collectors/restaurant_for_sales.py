import re
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.base import Collector
from app.schemas.ingestion import RawListing

SOURCE_NAME = "restaurant_for_sales"


class RestaurantForSalesResponseError(RuntimeError):
    pass


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.replace("\xa0", " ").split())
    return cleaned or None


def _money_value(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    match = re.fullmatch(r"\$?\s*(\d[\d,]*(?:\.\d{1,2})?)", cleaned)
    return match.group(1).replace(",", "") if match else None


def _whole_number(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    match = re.fullmatch(r"([\d,]+)(?:\+)?(?:\s*(?:sq\.?\s*ft\.?|sqft|sf))?", cleaned, re.I)
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
                if re.match(r"\s+County\b", text[match.end() :], flags=re.IGNORECASE):
                    continue
                matches.append((match.start(), city))
        if matches:
            return min(matches)[1]
    return None


def _is_food_service_listing(title: str, description: str | None) -> bool:
    if re.search(
        r"\b(?:beauty|nail|hair)\s+salon\b|\bpreschool\b|\bdaycare\b|"
        r"\bauto\s+body\b|\bdry\s+clean(?:er|ing)?\b|\bliquor\s+store\b|"
        r"\btrading\s+card\b",
        title,
        flags=re.IGNORECASE,
    ):
        return False
    combined = " ".join(item for item in (title, description) if item)
    return bool(
        re.search(
            r"\b(?:restaurant|cafe|coffee|tea|boba|bakery|dessert|beverage|food|"
            r"kitchen|bar|sushi|pizza|taco|sandwich|noodle|ramen|deli|juice|"
            r"smoothie)\b|café",
            combined,
            flags=re.IGNORECASE,
        )
    )


def parse_listing_candidates(
    html: str,
    *,
    site_url: str,
    target_cities: Sequence[str],
    target_counties: Sequence[str],
) -> list[tuple[str, str]]:
    """Return public detail URLs worth inspecting.

    County matches are only a request-scope optimization. The detail parser still
    requires an explicit target-city mention before emitting a listing.
    """

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    scope_terms = tuple(target_cities) + tuple(target_counties)

    for title_node in soup.select(".listing-title"):
        column = title_node.find_parent("div", class_="listing-col2")
        if column is None:
            continue
        image_column = column.find_previous_sibling("div", class_="listing-col1")
        anchor = image_column.find("a", href=True) if image_column is not None else None
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str) or "/restaurant-for-sale/" not in href:
            continue

        title = _clean_text(title_node.get_text(" ", strip=True)) or ""
        location_node = column.select_one(".listing-location")
        location = (
            _clean_text(location_node.get_text(" ", strip=True))
            if location_node is not None
            else ""
        ) or ""
        scope_text = f"{title} {location}"
        if not any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", scope_text, re.I)
            for term in scope_terms
        ):
            continue

        number_node = column.select_one(".listing-num")
        number_text = number_node.get_text(" ", strip=True) if number_node else ""
        number_match = re.search(r"#(\d+)", number_text)
        if number_match is None:
            continue
        external_id = number_match.group(1)
        if external_id in seen:
            continue
        seen.add(external_id)
        candidates.append((external_id, urljoin(f"{site_url.rstrip('/')}/", href)))
    return candidates


def _detail_pairs(soup: BeautifulSoup) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for row in soup.select(".details-layer"):
        cells = [
            cell
            for cell in row.find_all("div", recursive=False)
            if "simpleinline" in (cell.get("class") or [])
        ]
        if len(cells) < 2:
            continue
        key = _clean_text(cells[0].get_text(" ", strip=True))
        value = _clean_text(cells[1].get_text(" ", strip=True))
        if key and value:
            pairs[key.rstrip(":").casefold()] = value
    return pairs


def parse_listing_detail(
    html: str,
    *,
    external_id: str,
    target_cities: Sequence[str],
) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".details-title h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else None
    if title is None:
        raise RestaurantForSalesResponseError(
            f"RestaurantForSales listing {external_id} has no title"
        )

    body = soup.select_one(".simplebox .simpleinline.inline-9-12")
    description_node = body.find("p", recursive=False) if body is not None else None
    description = (
        _clean_text(description_node.get_text(" ", strip=True))
        if isinstance(description_node, Tag)
        else None
    )
    if not _is_food_service_listing(title, description):
        return None
    city = _infer_target_city(title, description, target_cities)
    if city is None:
        return None

    summary_node = soup.select_one(".details-title .simpleinlineright")
    summary_lines = (
        [item.strip() for item in summary_node.stripped_strings]
        if summary_node is not None
        else []
    )
    asking_price = next((_money_value(item) for item in summary_lines if _money_value(item)), None)
    status_text = next(
        (item for item in summary_lines if _money_value(item) is None), ""
    ).casefold()
    if "escrow" in status_text or "pending" in status_text:
        market_status = "pending"
    elif "sold" in status_text or "off market" in status_text:
        market_status = "off_market"
    elif "available" in status_text:
        market_status = "active"
    else:
        market_status = "unknown"

    pairs = _detail_pairs(soup)
    combined_text = " ".join(item for item in (title, description) if item)
    return {
        "title": title,
        "description": description,
        "city": city,
        "asking_price": asking_price,
        "monthly_rent": _money_value(pairs.get("total monthly rent")),
        "size_sqft": _whole_number(pairs.get("inside sq. ft.")),
        "type1_hood": _explicit_type1_hood(combined_text),
        "lease_terms": pairs.get("lease term"),
        "region_text": pairs.get("region"),
        "market_status": market_status,
    }


class RestaurantForSalesCollector(Collector):
    supports_reconciliation = True

    def __init__(
        self,
        *,
        site_url: str,
        target_cities: Sequence[str],
        target_counties: Sequence[str],
        timeout_seconds: float = 20,
        request_delay_seconds: float = 0.5,
        user_agent: str = "RestaurantScout/0.1",
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.site_url = site_url.rstrip("/")
        self.target_cities = tuple(target_cities)
        self.target_counties = tuple(target_counties)
        self.request_delay_seconds = max(0, request_delay_seconds)
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            transport=httpx.HTTPTransport(retries=2),
        )
        self._headers = {"User-Agent": user_agent, "Accept": "text/html"}

    @property
    def name(self) -> str:
        return SOURCE_NAME

    def _get(self, url: str) -> httpx.Response:
        response = self._client.get(url, headers=self._headers)
        response.raise_for_status()
        return response

    def collect(self) -> Iterable[RawListing]:
        try:
            index_url = f"{self.site_url}/restaurant-type/for-sale"
            response = self._get(index_url)
            candidates = parse_listing_candidates(
                response.text,
                site_url=self.site_url,
                target_cities=self.target_cities,
                target_counties=self.target_counties,
            )
            for external_id, source_url in candidates:
                self._sleep(self.request_delay_seconds)
                detail = self._get(source_url)
                payload = parse_listing_detail(
                    detail.text,
                    external_id=external_id,
                    target_cities=self.target_cities,
                )
                if payload is None:
                    continue
                yield RawListing(
                    source=SOURCE_NAME,
                    source_url=source_url,
                    external_id=external_id,
                    payload=payload,
                    collected_at=datetime.now(UTC),
                )
        finally:
            if self._owns_client:
                self._client.close()
