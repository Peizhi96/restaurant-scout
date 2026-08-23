import imaplib
import os
import unittest
from dataclasses import replace
from email.message import EmailMessage

os.environ["DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Base, ExternalLead, ExternalLeadDiscoveryMethod
from app.services.bizbuysell_email_alerts import extract_email_alert, sync_email_alerts


def alert_message(*, sender: str, html: str, subject: str = "New restaurant") -> bytes:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "scout@example.com"
    message["Subject"] = subject
    message.set_content("Open the HTML version to review this alert.")
    message.add_alternative(html, subtype="html")
    return message.as_bytes()


class FakeMailbox:
    messages: dict[bytes, bytes] = {}
    seen: list[bytes] = []
    search_calls: list[tuple[object, ...]] = []

    def __init__(self, host: str, port: int, *, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> "FakeMailbox":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def login(self, username: str, password: str) -> tuple[str, list[bytes]]:
        return "OK", [b"logged in"]

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        return "OK", [str(len(self.messages)).encode()]

    def logout(self) -> tuple[str, list[bytes]]:
        return "BYE", [b"logged out"]

    def uid(self, command: str, *args: object) -> tuple[str, list[object]]:
        if command == "search":
            self.search_calls.append(args)
            return "OK", [b" ".join(self.messages)]
        if command == "fetch":
            message_id = args[0]
            assert isinstance(message_id, bytes)
            return "OK", [(b"RFC822", self.messages[message_id])]
        if command == "store":
            message_id = args[0]
            assert isinstance(message_id, bytes)
            self.seen.append(message_id)
            return "OK", [b"stored"]
        raise AssertionError(f"Unexpected IMAP command: {command}")


class ReconnectingMailbox(FakeMailbox):
    connections = 0
    fetch_attempts = 0

    def __init__(self, host: str, port: int, *, timeout: int) -> None:
        super().__init__(host, port, timeout=timeout)
        type(self).connections += 1

    def uid(self, command: str, *args: object) -> tuple[str, list[object]]:
        if command == "fetch":
            type(self).fetch_attempts += 1
            if type(self).fetch_attempts == 1:
                raise imaplib.IMAP4.abort("socket error: EOF")
        return super().uid(command, *args)


class ExternalLeadApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.auth = {"X-Internal-API-Key": "test-internal-key"}

    def test_create_deduplicate_list_and_update_link_only_lead(self) -> None:
        created = self.client.post(
            "/api/external-leads",
            json={
                "source_url": (
                    "https://www.bizbuysell.com/Business-Opportunity/cafe/123/"
                    "?utm_source=email&msockid=tracking#details"
                ),
                "city": "san mateo",
                "notes": "Review location and contact path.",
            },
            headers=self.auth,
        )
        self.assertEqual(created.status_code, 200)
        lead = created.json()
        self.assertEqual(lead["source"], "BIZBUYSELL")
        self.assertEqual(lead["city"], "San Mateo")
        self.assertEqual(lead["status"], "NEW")
        self.assertEqual(lead["discovery_method"], "MANUAL")
        self.assertEqual(
            lead["source_url"],
            "https://www.bizbuysell.com/Business-Opportunity/cafe/123",
        )
        self.assertNotIn("title", lead)

        duplicate = self.client.post(
            "/api/external-leads",
            json={
                "source_url": (
                    "http://www.bizbuysell.com/Business-Opportunity/cafe/123/"
                    "?utm_campaign=second"
                ),
                "city": "Palo Alto",
            },
            headers=self.auth,
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["id"], lead["id"])
        with SessionLocal() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(ExternalLead)), 1)

        listed = self.client.get(
            "/api/external-leads", params={"source": "BIZBUYSELL"}
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        updated = self.client.patch(
            f"/api/external-leads/{lead['id']}",
            json={
                "city": "Palo Alto",
                "status": "CONTACT_BROKER",
                "notes": "Ask broker for independently supplied facts.",
            },
            headers=self.auth,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["city"], "Palo Alto")
        self.assertEqual(updated.json()["status"], "CONTACT_BROKER")

    def test_accepts_loopnet_and_filters(self) -> None:
        created = self.client.post(
            "/api/external-leads",
            json={
                "source_url": "https://www.loopnet.com/Listing/example/456/",
                "city": None,
            },
            headers=self.auth,
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["source"], "LOOPNET")
        self.assertIsNone(created.json()["city"])

        matches = self.client.get(
            "/api/external-leads", params={"status": "NEW", "source": "LOOPNET"}
        )
        self.assertEqual(matches.status_code, 200)
        self.assertEqual(len(matches.json()), 1)

        no_matches = self.client.get(
            "/api/external-leads", params={"source": "BIZBUYSELL"}
        )
        self.assertEqual(no_matches.status_code, 200)
        self.assertEqual(no_matches.json(), [])

    def test_rejects_non_source_homepage_and_non_target_city(self) -> None:
        invalid_urls = (
            "https://example.com/listing/1",
            "https://bizbuysell.com.evil.example/listing/1",
            "https://www.loopnet.com/",
        )
        for source_url in invalid_urls:
            with self.subTest(source_url=source_url):
                response = self.client.post(
                    "/api/external-leads",
                    json={"source_url": source_url},
                    headers=self.auth,
                )
                self.assertEqual(response.status_code, 422)

        outside_scope = self.client.post(
            "/api/external-leads",
            json={
                "source_url": "https://www.loopnet.com/Listing/example/789/",
                "city": "Oakland",
            },
            headers=self.auth,
        )
        self.assertEqual(outside_scope.status_code, 422)
        self.assertIn("P0 target cities", outside_scope.json()["detail"])

    def test_update_requires_existing_lead_and_nonempty_payload(self) -> None:
        missing = self.client.patch(
            "/api/external-leads/00000000-0000-0000-0000-000000000000",
            json={"status": "PASSED"},
            headers=self.auth,
        )
        self.assertEqual(missing.status_code, 404)

        created = self.client.post(
            "/api/external-leads",
            json={"source_url": "https://www.loopnet.com/Listing/example/999/"},
            headers=self.auth,
        )
        empty = self.client.patch(
            f"/api/external-leads/{created.json()['id']}",
            json={},
            headers=self.auth,
        )
        self.assertEqual(empty.status_code, 422)

    def test_email_parser_accepts_only_allowed_sender_and_listing_urls(self) -> None:
        message = alert_message(
            sender="BizBuySell Alerts <daily@notify.bizbuysell.com>",
            subject="New restaurants in San Mateo",
            html=(
                '<a href="https://www.bizbuysell.com/Business-Opportunity/cafe/123/'
                '?utm_source=email">Open listing</a>'
                '<a href="https://tracker.example/click?url=https%3A%2F%2Fwww.bizbuysell.com'
                '%2Fbusiness-asset%2Fturnkey-shop%2F456%2F">Tracked listing</a>'
                '<a href="https://www.bizbuysell.com/california/restaurants-for-sale/">'
                "Category page</a>"
            ),
        )
        extraction = extract_email_alert(
            message,
            allowed_sender_domains=("bizbuysell.com",),
            target_cities=("San Mateo", "San Carlos"),
        )
        assert extraction is not None
        self.assertEqual(extraction.city, "San Mateo")
        self.assertEqual(
            extraction.urls,
            (
                "https://www.bizbuysell.com/Business-Opportunity/cafe/123",
                "https://www.bizbuysell.com/business-asset/turnkey-shop/456",
            ),
        )

        rejected = extract_email_alert(
            alert_message(
                sender="Fake Alerts <daily@bizbuysell.com.evil.example>",
                html='<a href="https://www.bizbuysell.com/business-opportunity/x/1/">x</a>',
            ),
            allowed_sender_domains=("bizbuysell.com",),
            target_cities=("San Mateo",),
        )
        self.assertIsNone(rejected)

    def test_imap_sync_creates_deduplicated_email_alert_leads_and_audit(self) -> None:
        FakeMailbox.messages = {
            b"1": alert_message(
                sender="alerts@bizbuysell.com",
                subject="Palo Alto restaurant matches",
                html=(
                    '<a href="https://www.bizbuysell.com/business-opportunity/a/101/">'
                    "Listing A</a>"
                ),
            ),
            b"2": alert_message(
                sender="alerts@other.example",
                html=(
                    '<a href="https://www.bizbuysell.com/business-opportunity/b/202/">'
                    "Untrusted</a>"
                ),
            ),
        }
        FakeMailbox.seen = []
        FakeMailbox.search_calls = []
        settings = replace(
            get_settings(),
            bizbuysell_email_alerts_enabled=True,
            bizbuysell_imap_host="imap.example.com",
            bizbuysell_imap_username="scout@example.com",
            bizbuysell_imap_password="test-only",
            bizbuysell_email_allowed_sender_domains=("bizbuysell.com",),
        )
        with SessionLocal() as db:
            first = sync_email_alerts(
                db, settings=settings, mailbox_factory=FakeMailbox
            )
            second = sync_email_alerts(
                db, settings=settings, mailbox_factory=FakeMailbox
            )

            leads = list(db.scalars(select(ExternalLead)))
            self.assertEqual(len(leads), 1)
            self.assertEqual(leads[0].city, "Palo Alto")
            self.assertEqual(
                leads[0].discovery_method,
                ExternalLeadDiscoveryMethod.EMAIL_ALERT,
            )
            self.assertEqual(first.messages_scanned, 1)
            self.assertEqual(first.links_found, 1)
            self.assertEqual(first.leads_created, 1)
            self.assertEqual(second.leads_existing, 1)
            self.assertEqual(FakeMailbox.seen, [b"1", b"1"])
            self.assertTrue(
                all("FROM" in call for call in FakeMailbox.search_calls)
            )

    def test_imap_sync_reconnects_once_after_fetch_eof(self) -> None:
        ReconnectingMailbox.messages = {
            b"1": alert_message(
                sender="alerts@bizbuysell.com",
                html=(
                    '<a href="https://www.bizbuysell.com/business-opportunity/a/303/">'
                    "Listing A</a>"
                ),
            )
        }
        ReconnectingMailbox.seen = []
        ReconnectingMailbox.search_calls = []
        ReconnectingMailbox.connections = 0
        ReconnectingMailbox.fetch_attempts = 0
        settings = replace(
            get_settings(),
            bizbuysell_email_alerts_enabled=True,
            bizbuysell_imap_host="imap.example.com",
            bizbuysell_imap_username="scout@example.com",
            bizbuysell_imap_password="test-only",
            bizbuysell_email_allowed_sender_domains=("bizbuysell.com",),
        )

        with SessionLocal() as db:
            run = sync_email_alerts(
                db, settings=settings, mailbox_factory=ReconnectingMailbox
            )

        self.assertEqual(run.status.value, "SUCCEEDED")
        self.assertEqual(run.leads_created, 1)
        self.assertEqual(ReconnectingMailbox.connections, 2)
        self.assertEqual(ReconnectingMailbox.fetch_attempts, 2)

    def test_email_sync_status_endpoint_is_protected(self) -> None:
        unauthorized = self.client.get(
            "/api/external-leads/bizbuysell-email/status"
        )
        self.assertEqual(unauthorized.status_code, 401)
        status_response = self.client.get(
            "/api/external-leads/bizbuysell-email/status", headers=self.auth
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertFalse(status_response.json()["enabled"])
        self.assertIsNone(status_response.json()["latest_run"])


if __name__ == "__main__":
    unittest.main()
