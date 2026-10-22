"""Configuration and small HTTP helpers shared by the end-to-end suite."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:3001").rstrip("/")
API_URL = os.environ.get("E2E_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("INTERNAL_API_KEY", "local-dev-only-change-me")
AUTH_USER = os.environ.get("APP_AUTH_USERNAME", "")
AUTH_PASSWORD = os.environ.get("APP_AUTH_PASSWORD", "")
HEADLESS = os.environ.get("E2E_HEADLESS", "true").lower() != "false"
READY_TIMEOUT_SECONDS = float(os.environ.get("E2E_READY_TIMEOUT", "180"))
ALLOW_REMOTE = os.environ.get("E2E_ALLOW_REMOTE") == "1"

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def assert_local_target() -> None:
    """The suite writes test listings, so it refuses to run against a remote stack by default."""
    for url in (BASE_URL, API_URL):
        host = urlparse(url).hostname
        if host not in LOCAL_HOSTS and not ALLOW_REMOTE:
            raise RuntimeError(
                f"Refusing to seed test data into {url}. "
                "Point E2E_BASE_URL/E2E_API_URL at a local stack or set E2E_ALLOW_REMOTE=1."
            )


def basic_auth_header(user: str = AUTH_USER, password: str = AUTH_PASSWORD) -> dict[str, str]:
    if not user:
        return {}
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@dataclass(frozen=True)
class SeededListing:
    id: str
    title: str
    city: str


@dataclass(frozen=True)
class SeededListings:
    palo_alto: SeededListing
    san_mateo: SeededListing
    sunnyvale: SeededListing

    @property
    def all(self) -> list[SeededListing]:
        return [self.palo_alto, self.san_mateo, self.sunnyvale]


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


def http(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: Any = None,
    timeout: float = 15.0,
) -> HttpResult:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResult(
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as error:
        return HttpResult(
            error.code,
            {key.lower(): value for key, value in error.headers.items()},
            error.read(),
        )


class ApiClient:
    """Talks to the FastAPI service directly to seed data and check persisted state."""

    def __init__(self, base_url: str = API_URL, api_key: str = API_KEY) -> None:
        self.base_url = base_url
        self.headers = {"X-Internal-API-Key": api_key}

    def get(self, path: str) -> HttpResult:
        return http("GET", f"{self.base_url}{path}", headers=self.headers)

    def post(self, path: str, payload: Any) -> HttpResult:
        return http("POST", f"{self.base_url}{path}", headers=self.headers, payload=payload)

    def listing(self, listing_id: str) -> dict[str, Any]:
        result = self.get(f"/api/listings/{listing_id}")
        if result.status != 200:
            raise AssertionError(
                f"GET listing {listing_id} returned {result.status}: {result.body!r}"
            )
        return result.json()


def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float,
    message: str,
    interval: float = 1.0,
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception as error:  # keep polling through transient startup errors
            last_error = error
        time.sleep(interval)
    raise TimeoutError(f"{message} (last error: {last_error!r})")
