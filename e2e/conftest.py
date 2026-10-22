"""Fixtures for the Restaurant Scout end-to-end suite.

The suite drives a real Chrome browser through Selenium WebDriver against the running
Next.js dashboard, which calls the real FastAPI service backed by PostgreSQL. Test data
is seeded through the manual-ingestion API, so every listing goes through the same
normalization, deduplication, and scoring path as production data.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from support import (
    AUTH_USER,
    BASE_URL,
    HEADLESS,
    READY_TIMEOUT_SECONDS,
    ApiClient,
    SeededListing,
    SeededListings,
    assert_local_target,
    basic_auth_header,
    http,
    wait_until,
)

ARTIFACTS = Path(__file__).parent / "artifacts"


@pytest.fixture(scope="session")
def api() -> ApiClient:
    return ApiClient()


@pytest.fixture(scope="session", autouse=True)
def stack_ready(api: ApiClient) -> None:
    """Wait for PostgreSQL migrations, the API, and the dashboard before any test runs."""
    assert_local_target()
    wait_until(
        lambda: api.get("/readyz").status == 200,
        timeout=READY_TIMEOUT_SECONDS,
        message="API /readyz never became ready",
        interval=2.0,
    )
    wait_until(
        lambda: http("GET", f"{BASE_URL}/dashboard", headers=basic_auth_header()).status == 200,
        timeout=READY_TIMEOUT_SECONDS,
        message="Dashboard never returned 200",
        interval=2.0,
    )


@pytest.fixture(scope="session")
def seeded(api: ApiClient) -> SeededListings:
    """Ingest three uniquely named listings through the real manual-ingestion pipeline."""
    run_tag = uuid.uuid4().hex[:8]
    specs = {
        "palo_alto": {
            "title": f"E2E Palo Alto Commissary Kitchen {run_tag}",
            "city": "Palo Alto",
            "address": f"101 E2E Test Way Unit {run_tag}",
            "zip": "94301",
            "asking_price": 240000,
            "monthly_rent": 6800,
            "size_sqft": 1900,
            "seats": 30,
            "parking": True,
            "type1_hood": True,
        },
        "san_mateo": {
            "title": f"E2E San Mateo Corner Cafe {run_tag}",
            "city": "San Mateo",
            "address": f"202 E2E Test Way Unit {run_tag}",
            "zip": "94401",
            "asking_price": 180000,
            "monthly_rent": 5200,
            "size_sqft": 1400,
            "seats": 45,
            "parking": False,
            "type1_hood": True,
        },
        "sunnyvale": {
            "title": f"E2E Sunnyvale Noodle House {run_tag}",
            "city": "Sunnyvale",
            "address": f"303 E2E Test Way Unit {run_tag}",
            "zip": "94086",
            "asking_price": 295000,
            "monthly_rent": 7600,
            "size_sqft": 2200,
            "seats": 60,
            "parking": True,
            "type1_hood": True,
        },
    }
    items = [
        {
            "source_url": f"https://example.com/e2e/{run_tag}/{key}",
            "external_id": f"e2e-{run_tag}-{key}",
            "payload": {
                **payload,
                "description": "Seeded by the Selenium end-to-end suite.",
            },
        }
        for key, payload in specs.items()
    ]

    result = api.post("/api/jobs/manual", {"items": items})
    assert result.status == 200, f"manual ingestion failed: {result.status} {result.body!r}"
    run = result.json()
    assert run["status"] == "COMPLETED" and run["succeeded_count"] == len(items), run

    listings = api.get("/api/listings?limit=200&sort_by=recent").json()
    by_title = {listing["title"]: listing for listing in listings}
    seeded: dict[str, SeededListing] = {}
    for key, payload in specs.items():
        listing = by_title.get(payload["title"])
        assert listing is not None, f"seeded listing not found via API: {payload['title']}"
        seeded[key] = SeededListing(id=listing["id"], title=payload["title"], city=payload["city"])
    return SeededListings(**seeded)


@pytest.fixture
def driver() -> Iterator[webdriver.Chrome]:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    for argument in ("--no-sandbox", "--disable-dev-shm-usage", "--window-size=1440,1000"):
        options.add_argument(argument)
    if binary := os.environ.get("CHROME_BINARY"):
        options.binary_location = binary
    chromedriver = os.environ.get("CHROMEDRIVER_PATH")
    service = Service(executable_path=chromedriver) if chromedriver else Service()

    browser = webdriver.Chrome(options=options, service=service)
    browser.set_page_load_timeout(60)
    if AUTH_USER:
        # The dashboard sits behind HTTP Basic auth; send the operator credentials on
        # every request the page makes, including server-action POSTs.
        browser.execute_cdp_cmd("Network.enable", {})
        browser.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": basic_auth_header()})
    yield browser
    browser.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):  # type: ignore[no-untyped-def]
    """Save a screenshot and the page HTML for any failed browser test (uploaded by CI)."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    browser = getattr(item, "funcargs", {}).get("driver")
    if browser is None:
        return
    ARTIFACTS.mkdir(exist_ok=True)
    stem = item.nodeid.replace("/", "_").replace("::", "__")
    browser.save_screenshot(str(ARTIFACTS / f"{stem}.png"))
    (ARTIFACTS / f"{stem}.html").write_text(browser.page_source, encoding="utf-8")
