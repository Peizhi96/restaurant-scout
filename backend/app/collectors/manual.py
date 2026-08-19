from collections.abc import Iterable

from app.collectors.base import Collector
from app.schemas.ingestion import RawListing


class ManualCollector(Collector):
    def __init__(self, items: Iterable[RawListing]) -> None:
        self._items = tuple(items)

    @property
    def name(self) -> str:
        return "manual"

    def collect(self) -> Iterable[RawListing]:
        return iter(self._items)
