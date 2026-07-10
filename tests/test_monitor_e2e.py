"""End-to-end wiring test: fetch -> filter -> format -> send -> mark_seen,
with the IMAP and Telegram boundaries replaced by fakes (no network, no creds)."""

from config import Config
from email_client import EmailMessage
from email2telegram import EmailMonitor


def make_config(**overrides):
    base = dict(
        email_address="me@example.com",
        email_password="pw",
        imap_server="imap.example.com",
        telegram_bot_token="TOKEN",
        telegram_chat_id="12345",
        filter_subject="Last War",
        filter_body="Email",
        imap_folders="inbox,Spam",
    )
    base.update(overrides)
    return Config(_env_file=None, **base)


class FakeEmailClient:
    def __init__(self, emails):
        self._emails = emails
        self.marked = []
        self.connected = True

    def is_connected(self):
        return self.connected

    def reconnect(self):
        self.connected = True

    def fetch_unread(self, folders, since_days=None, subject=None):
        return self._emails

    def mark_seen(self, email_id, folder):
        self.marked.append((email_id, folder))

    def connect(self):
        pass

    def close(self):
        pass


class FakeTelegramClient:
    def __init__(self):
        self.sent = []

    def send(self, message, parse_mode="HTML"):
        self.sent.append(message)


def build_monitor(emails):
    monitor = EmailMonitor(make_config())
    monitor.email_client = FakeEmailClient(emails)
    monitor.telegram_client = FakeTelegramClient()
    return monitor


def test_matching_email_is_forwarded_and_marked_seen():
    email = EmailMessage(
        subject="[Last War] Account Sign In",
        sender="alice@example.com",
        body="Please verify your Email now",
        folder="inbox",
        email_id="42",
    )
    monitor = build_monitor([email])
    monitor._check_once()

    assert len(monitor.telegram_client.sent) == 1
    sent = monitor.telegram_client.sent[0]
    assert "[Last War] Account Sign In" in sent
    assert "alice@example.com" in sent
    assert monitor.email_client.marked == [("42", "inbox")]


def test_non_matching_email_is_skipped():
    email = EmailMessage(
        subject="Newsletter",
        sender="news@example.com",
        body="Nothing relevant here",
        folder="inbox",
        email_id="7",
    )
    monitor = build_monitor([email])
    monitor._check_once()

    assert monitor.telegram_client.sent == []
    assert monitor.email_client.marked == []


def test_reconnects_when_connection_stale():
    monitor = build_monitor([])
    monitor.email_client.connected = False
    monitor._check_once()
    # after a stale connection, _check_once should have triggered reconnect
    assert monitor.email_client.connected is True


def test_telegram_failure_does_not_mark_seen():
    email = EmailMessage(
        subject="[Last War] Account Sign In",
        sender="alice@example.com",
        body="verify your Email",
        folder="inbox",
        email_id="99",
    )
    monitor = build_monitor([email])

    def boom(message, parse_mode="HTML"):
        raise RuntimeError("telegram down")

    monitor.telegram_client.send = boom
    monitor._check_once()  # must not raise

    # send failed, so the email should NOT be marked seen (it can retry later)
    assert monitor.email_client.marked == []
