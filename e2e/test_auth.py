"""The dashboard must reject requests without valid operator credentials."""

import pytest

from support import AUTH_PASSWORD, AUTH_USER, BASE_URL, basic_auth_header, http

pytestmark = pytest.mark.skipif(
    not AUTH_USER, reason="APP_AUTH_USERNAME is not set, so dashboard auth is disabled"
)


def test_dashboard_requires_credentials() -> None:
    result = http("GET", f"{BASE_URL}/dashboard")

    assert result.status == 401
    assert result.headers.get("www-authenticate", "").startswith("Basic")


def test_dashboard_rejects_wrong_password() -> None:
    result = http(
        "GET",
        f"{BASE_URL}/dashboard",
        headers=basic_auth_header(AUTH_USER, AUTH_PASSWORD + "-wrong"),
    )

    assert result.status == 401


def test_dashboard_accepts_operator_credentials() -> None:
    result = http("GET", f"{BASE_URL}/dashboard", headers=basic_auth_header())

    assert result.status == 200
