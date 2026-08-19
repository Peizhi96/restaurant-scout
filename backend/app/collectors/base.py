from abc import ABC, abstractmethod
from collections.abc import Iterable

from app.schemas.ingestion import RawListing


class Collector(ABC):
    supports_reconciliation = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable collector identifier stored with every collection run."""

    @abstractmethod
    def collect(self) -> Iterable[RawListing]:
        """Return raw source records without applying business normalization."""
