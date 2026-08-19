import unittest
from urllib.parse import parse_qs

import httpx

from app.collectors.restaurant_realty import (
    RestaurantRealtyCollector,
    parse_listing_detail,
    parse_listing_ids,
)


def _list_html(*listing_ids: str) -> str:
    links = "".join(
        f"<div><a href='/listing/?listing={listing_id}-Example'>Listing</a></div>"
        for listing_id in listing_ids
    )
    return f"<div id='bbcrm-listings-searchresults'>{links}</div>"


def _detail_html(title: str, description: str) -> str:
    return f"""
    <div id="bbcrm-listing">
      <div id="maintitle">{title}</div>
      <div class="soldremove">Offered At $150,000</div>
      <div class="datablock">
        <div class="datahead">Type</div>
        <div class="datainfo">Cafe, Bring Your Own Concept</div>
      </div>
      <div id="maindesc">{description}</div>
      <div class="detailblock">
        <div class="detaillable">Square Feet</div>
        <div class="detailinfo">1,300</div>
        <div class="detaillable">Seating</div>
        <div class="detailinfo">Contact For Info</div>
        <div class="detaillable">Parking</div>
        <div class="detailinfo">Metered Street Parking</div>
      </div>
      <div class="detailblock">
        <div class="detaillable">Rent</div>
        <div class="detailinfo">10,683.88 (all in)</div>
        <div class="detaillable">Expiration</div>
        <div class="detailinfo">2027</div>
      </div>
    </div>
    """


class RestaurantRealtyCollectorTestCase(unittest.TestCase):
    def test_list_parser_deduplicates_external_ids(self) -> None:
        html = _list_html("5356", "5356", "5345")
        self.assertEqual(parse_listing_ids(html), ["5356", "5345"])

    def test_detail_parser_preserves_unknowns_and_explicit_negative(self) -> None:
        payload = parse_listing_detail(
            _detail_html(
                "Prime Downtown Palo Alto Opportunity",
                "The premises are configured without a Type I hood.",
            ),
            external_id="5356",
            target_cities=("San Mateo", "Palo Alto"),
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["city"], "Palo Alto")
        self.assertEqual(payload["asking_price"], "150000")
        self.assertEqual(payload["monthly_rent"], "10683.88")
        self.assertEqual(payload["size_sqft"], "1300")
        self.assertIsNone(payload["seats"])
        self.assertIsNone(payload["parking"])
        self.assertEqual(payload["parking_text"], "Metered Street Parking")
        self.assertFalse(payload["type1_hood"])

    def test_county_name_is_not_guessed_as_city(self) -> None:
        payload = parse_listing_detail(
            _detail_html(
                "San Mateo County Restaurant",
                "A confidential opportunity elsewhere in San Mateo County.",
            ),
            external_id="9999",
            target_cities=("San Mateo",),
        )
        self.assertIsNone(payload)

    def test_collector_queries_target_counties_and_emits_only_target_city(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            form = parse_qs(request.content.decode())
            if request.url.path.endswith("/submitsearchtoolnew"):
                return httpx.Response(
                    200,
                    json={
                        "code": 200,
                        "type": "listings",
                        "body": {"html": _list_html("5356", "9999")},
                    },
                )
            source_url = form["url"][0]
            if source_url.endswith("5356"):
                html = _detail_html(
                    "Prime Downtown Palo Alto Opportunity",
                    "An explicit Palo Alto location with a Type 1 hood.",
                )
            else:
                html = _detail_html(
                    "Confidential Santa Clara County Restaurant",
                    "The exact city is not publicly stated.",
                )
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "type": "listings",
                    "body": {"listing_id": source_url.rsplit("=", 1)[-1], "html": html},
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        collector = RestaurantRealtyCollector(
            site_url="https://restaurantrealty.com",
            api_url="https://api.restaurantrealty.test/api/bbcrmapi",
            target_cities=("Palo Alto",),
            target_counties=("San Mateo County", "Santa Clara County"),
            request_delay_seconds=0,
            client=client,
        )

        items = list(collector.collect())

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].external_id, "5356")
        self.assertEqual(items[0].payload["city"], "Palo Alto")
        self.assertTrue(items[0].payload["type1_hood"])
        search_requests = [
            request
            for request in requests
            if request.url.path.endswith("/submitsearchtoolnew")
        ]
        detail_requests = [
            request for request in requests if request.url.path.endswith("/listing")
        ]
        self.assertEqual(len(search_requests), 2)
        self.assertEqual(len(detail_requests), 2)
        self.assertTrue(
            all(
                request.headers["origin"] == "https://restaurantrealty.com"
                for request in requests
            )
        )
        searches = [
            parse_qs(request.content.decode())["search"][0]
            for request in search_requests
        ]
        self.assertTrue(any("San Mateo County" in search for search in searches))
        self.assertTrue(any("Santa Clara County" in search for search in searches))


if __name__ == "__main__":
    unittest.main()
