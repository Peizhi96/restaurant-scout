from collections.abc import Sequence

import httpx

from app.collectors.authorized_feed import AuthorizedJsonFeedCollector

SOURCE_NAME = "bizbuysell"


class BizBuySellCollector(AuthorizedJsonFeedCollector):
    """Adapter for a separately authorized BizBuySell JSON feed or export.

    BizBuySell's public website is not crawled by this collector. Enabling it requires
    an operator-configured feed obtained under permission that allows automated access
    and storage in Restaurant Scout.
    """

    def __init__(
        self,
        *,
        feed_url: str,
        target_cities: Sequence[str],
        feed_is_complete: bool = False,
        bearer_token: str | None = None,
        timeout_seconds: float = 20,
        user_agent: str = "RestaurantScout/0.1",
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            source_name=SOURCE_NAME,
            feed_url=feed_url,
            allowed_listing_hosts=("bizbuysell.com",),
            target_cities=target_cities,
            feed_is_complete=feed_is_complete,
            bearer_token=bearer_token,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            client=client,
        )
