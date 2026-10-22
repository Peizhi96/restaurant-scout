"""Browser tests for the core operator workflow: discover, filter, inspect, and review."""

import uuid

from pages import DashboardPage, ListingDetailPage, ListingsPage
from support import BASE_URL, ApiClient, SeededListings, wait_until


def test_dashboard_shows_newly_ingested_listings(driver, seeded: SeededListings) -> None:
    dashboard = DashboardPage(driver, BASE_URL).open()

    assert dashboard.heading() == "Your acquisition radar."
    dashboard.wait_for_recent_titles([listing.title for listing in seeded.all])


def test_city_filter_narrows_results_and_clear_restores_them(
    driver, seeded: SeededListings
) -> None:
    listings = ListingsPage(driver, BASE_URL).open()
    listings.wait_for_titles(present=[listing.title for listing in seeded.all])

    listings.filter_by_city("Palo Alto")
    listings.wait_for_titles(
        present=[seeded.palo_alto.title],
        absent=[seeded.san_mateo.title, seeded.sunnyvale.title],
    )

    listings.clear_filters()
    listings.wait_for_titles(present=[listing.title for listing in seeded.all])


def test_listing_detail_shows_scores_and_unknown_facts(driver, seeded: SeededListings) -> None:
    listing = seeded.palo_alto
    detail = ListingsPage(driver, BASE_URL).open().open_listing(listing.title)

    assert driver.current_url.endswith(f"/listings/{listing.id}")
    assert detail.score_panel_heading() == "Two lenses, kept separate"
    # Grease trap and walk-in cooler were never supplied: they must stay explicit unknowns.
    assert detail.missing_information(), "unknown kitchen facts should be listed as missing"
    # OpenAI is disabled in this environment, so no AI explanation exists yet.
    assert detail.ai_panel_heading() == "Not generated"


def test_operator_review_persists_and_drives_pipeline_filter(
    driver, seeded: SeededListings, api: ApiClient
) -> None:
    listing = seeded.sunnyvale
    note = f"Broker call booked, lease review pending ({uuid.uuid4().hex[:6]})"

    detail = ListingDetailPage(driver, BASE_URL).open(listing.id, listing.title)
    detail.save_review(status="REVIEWING", notes=note)

    # The server action writes through the API; confirm the change actually persisted.
    wait_until(
        lambda: api.listing(listing.id)["status"] == "REVIEWING",
        timeout=20,
        message="listing status never changed to REVIEWING",
    )
    assert api.listing(listing.id)["notes"] == note

    driver.refresh()
    detail.wait_loaded(listing.title)
    assert detail.review_values() == ("REVIEWING", note)

    ListingsPage(driver, BASE_URL).open("status=REVIEWING").wait_for_titles(
        present=[listing.title],
        absent=[seeded.palo_alto.title, seeded.san_mateo.title],
    )
