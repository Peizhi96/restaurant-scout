import unittest

import httpx

from app.collectors.restaurant_for_sales import (
    RestaurantForSalesCollector,
    parse_listing_candidates,
    parse_listing_detail,
)

LIST_HTML = """
<div class='inline-container' style='border:1px solid black;'>
  <div class='listing-col1'>
    <a href='/restaurant-for-sale/downtown-san-mateo-cafe'><img></a>
  </div>
  <div class='listing-col2'>
    <div class='listing-num'>#6898</div>
    <div class='listing-title'>Cafe opportunity in Downtown San Mateo</div>
    <div class='listing-location'>San Mateo County</div>
  </div>
</div>
<div class='inline-container' style='border:1px solid black;'>
  <div class='listing-col1'>
    <a href='/restaurant-for-sale/confidential-county-listing'><img></a>
  </div>
  <div class='listing-col2'>
    <div class='listing-num'>#7000</div>
    <div class='listing-title'>Confidential restaurant opportunity</div>
    <div class='listing-location'>Santa Clara County</div>
  </div>
</div>
"""


def _detail_html(
    *, title: str, description: str, status: str = "Available", listing_id: str = "6898"
) -> str:
    return f"""
    <div class='details-title'>
      <div class='simpleinline inline-3-12'>#{listing_id}<br>San Mateo County</div>
      <div class='simpleinline inline-6-12'><h1>{title}</h1></div>
      <div class='simpleinlineright inline-3-12'>$288,000<br>{status}</div>
    </div>
    <div class='simplebox'>
      <div class='simpleinline inline-9-12'>
        <p>{description}</p>
        <div class='details-layer'>
          <div class='simpleinline inline-6-12'>Total Monthly Rent:</div>
          <div class='simpleinline inline-6-12'>$2,800</div>
        </div>
        <div class='details-layer'>
          <div class='simpleinline inline-6-12'>Inside Sq. Ft.:</div>
          <div class='simpleinline inline-6-12'>700+</div>
        </div>
      </div>
    </div>
    """


class RestaurantForSalesCollectorTestCase(unittest.TestCase):
    def test_candidate_parser_scopes_requests_and_deduplicates(self) -> None:
        candidates = parse_listing_candidates(
            LIST_HTML + LIST_HTML,
            site_url="https://restaurantforsales.com",
            target_cities=("San Mateo", "Palo Alto"),
            target_counties=("San Mateo County", "Santa Clara County"),
        )
        self.assertEqual(
            candidates,
            [
                ("6898", "https://restaurantforsales.com/restaurant-for-sale/downtown-san-mateo-cafe"),
                ("7000", "https://restaurantforsales.com/restaurant-for-sale/confidential-county-listing"),
            ],
        )

    def test_detail_parser_preserves_unknowns_and_pending_status(self) -> None:
        payload = parse_listing_detail(
            _detail_html(
                title="Cafe opportunity in Downtown San Mateo",
                description="A compact cafe configured without a Type I hood.",
                status="In Escrow",
            ),
            external_id="6898",
            target_cities=("San Mateo", "Palo Alto"),
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["city"], "San Mateo")
        self.assertEqual(payload["asking_price"], "288000")
        self.assertEqual(payload["monthly_rent"], "2800")
        self.assertEqual(payload["size_sqft"], "700")
        self.assertFalse(payload["type1_hood"])
        self.assertEqual(payload["market_status"], "pending")

    def test_county_only_detail_is_not_emitted(self) -> None:
        payload = parse_listing_detail(
            _detail_html(
                title="Confidential Santa Clara County restaurant",
                description="Contact the broker for the city.",
                listing_id="7000",
            ),
            external_id="7000",
            target_cities=("Santa Clara",),
        )
        self.assertIsNone(payload)

    def test_non_food_business_on_source_page_is_not_emitted(self) -> None:
        payload = parse_listing_detail(
            _detail_html(
                title="Asset sale only - Beauty salon for sale in Mountain View",
                description="Six hair stations in a bright salon near Highway 101.",
            ),
            external_id="7999",
            target_cities=("Mountain View",),
        )
        self.assertIsNone(payload)

    def test_collector_uses_public_pages_and_emits_only_explicit_city(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path == "/restaurant-type/for-sale":
                return httpx.Response(200, text=LIST_HTML)
            if request.url.path.endswith("downtown-san-mateo-cafe"):
                return httpx.Response(
                    200,
                    text=_detail_html(
                        title="Cafe opportunity in Downtown San Mateo",
                        description="Public listing details with a Type 1 hood.",
                    ),
                )
            return httpx.Response(
                200,
                text=_detail_html(
                    title="Confidential Santa Clara County restaurant",
                    description="The exact city is not publicly stated.",
                    listing_id="7000",
                ),
            )

        collector = RestaurantForSalesCollector(
            site_url="https://restaurantforsales.com",
            target_cities=("San Mateo", "Santa Clara"),
            target_counties=("San Mateo County", "Santa Clara County"),
            request_delay_seconds=0,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        items = list(collector.collect())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].external_id, "6898")
        self.assertEqual(items[0].payload["city"], "San Mateo")
        self.assertTrue(items[0].payload["type1_hood"])
        self.assertEqual(len(requests), 3)
        self.assertTrue(
            all(
                request.headers["user-agent"] == "RestaurantScout/0.1"
                for request in requests
            )
        )


if __name__ == "__main__":
    unittest.main()
