import unittest

import httpx

from app.collectors.authorized_feed import AuthorizedFeedError
from app.collectors.bizbuysell import BizBuySellCollector
from app.collectors.loopnet import LoopNetCollector


class AuthorizedFeedCollectorTestCase(unittest.TestCase):
    def test_bizbuysell_reads_one_authorized_feed_and_filters_target_city(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "external_id": "bbs-101",
                            "source_url": "https://www.bizbuysell.com/Business-Opportunity/example/101/",
                            "collected_at": "2026-08-19T12:00:00Z",
                            "payload": {
                                "title": "Restaurant asset sale",
                                "city": "san mateo",
                                "asking_price": "250000",
                                "type1_hood": None,
                                "market_status": "active",
                            },
                        },
                        {
                            "external_id": "bbs-102",
                            "source_url": "https://www.bizbuysell.com/Business-Opportunity/example/102/",
                            "payload": {
                                "title": "Restaurant outside the target corridor",
                                "city": "Oakland",
                            },
                        },
                        {
                            "external_id": "bbs-103",
                            "source_url": "https://www.bizbuysell.com/Business-Opportunity/example/103/",
                            "payload": {
                                "title": "Beauty salon asset sale",
                                "city": "San Mateo",
                            },
                        },
                    ]
                },
            )

        collector = BizBuySellCollector(
            feed_url="https://authorized-feed.example/bizbuysell.json",
            bearer_token="licensed-token",
            target_cities=("San Mateo", "Palo Alto"),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        items = list(collector.collect())

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, "/bizbuysell.json")
        self.assertEqual(requests[0].headers["authorization"], "Bearer licensed-token")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "bizbuysell")
        self.assertEqual(items[0].external_id, "bbs-101")
        self.assertEqual(items[0].payload["city"], "San Mateo")
        self.assertIsNone(items[0].payload["type1_hood"])

    def test_loopnet_accepts_list_contract_and_can_mark_full_feed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    {
                        "external_id": "ln-202",
                        "source_url": "https://www.loopnet.com/Listing/example/202/",
                        "payload": {
                            "title": "Second-generation restaurant space",
                            "city": "Sunnyvale",
                            "monthly_rent": None,
                            "market_status": "active",
                        },
                    }
                ],
            )

        collector = LoopNetCollector(
            feed_url="https://licensed-export.example/loopnet.json",
            target_cities=("Sunnyvale",),
            feed_is_complete=True,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        items = list(collector.collect())

        self.assertTrue(collector.supports_reconciliation)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "loopnet")
        self.assertIsNone(items[0].payload["monthly_rent"])

    def test_feed_rejects_html_and_never_treats_a_page_as_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>public search page</html>")

        collector = LoopNetCollector(
            feed_url="https://licensed-export.example/not-a-feed",
            target_cities=("Palo Alto",),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with self.assertRaisesRegex(AuthorizedFeedError, "did not return JSON"):
            list(collector.collect())

    def test_source_listing_host_must_match_collector(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    {
                        "external_id": "bad-host",
                        "source_url": "https://example.com/not-loopnet",
                        "payload": {"title": "Restaurant", "city": "Palo Alto"},
                    }
                ],
            )

        collector = LoopNetCollector(
            feed_url="https://licensed-export.example/loopnet.json",
            target_cities=("Palo Alto",),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with self.assertRaisesRegex(AuthorizedFeedError, "not valid for loopnet"):
            list(collector.collect())


if __name__ == "__main__":
    unittest.main()
