from email_client import EmailClient, IMAPConnectionError


RAW_EMAIL = (
    b"From: Alice <alice@example.com>\r\n"
    b"Subject: [Last War] Account Sign In\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"Please verify your Email now.\r\n"
)


class FakeIMAP:
    """Minimal stand-in for imaplib.IMAP4_SSL."""

    def __init__(self, unseen_ids=(b"1",), alive=True):
        self._unseen = list(unseen_ids)
        self._alive = alive
        self.stored = []
        self.last_search = None
        self.last_fetch_parts = None

    def noop(self):
        if not self._alive:
            raise OSError("connection dead")
        return ("OK", [b"NOOP completed"])

    def select(self, folder):
        return ("OK", [b"1"])

    def search(self, charset, *criteria):
        self.last_search = criteria
        return ("OK", [b" ".join(self._unseen)])

    def fetch(self, email_id, parts):
        self.last_fetch_parts = parts
        return ("OK", [(b"1 (RFC822 {123}", RAW_EMAIL)])

    def store(self, email_id, flags, value):
        self.stored.append((email_id, flags, value))
        return ("OK", [b"stored"])

    def close(self):
        pass

    def logout(self):
        pass


def _client_with(fake):
    c = EmailClient(config=None)
    c._mail = fake
    return c


def test_is_connected_true_when_noop_ok():
    assert _client_with(FakeIMAP()).is_connected() is True


def test_is_connected_false_when_noop_fails():
    assert _client_with(FakeIMAP(alive=False)).is_connected() is False


def test_is_connected_false_when_no_mail():
    assert EmailClient(config=None).is_connected() is False


def test_fetch_unread_parses_message():
    client = _client_with(FakeIMAP(unseen_ids=(b"1",)))
    messages = client.fetch_unread(["inbox"])

    assert len(messages) == 1
    msg = messages[0]
    assert msg.subject == "[Last War] Account Sign In"
    assert "alice@example.com" in msg.sender
    assert "verify your Email" in msg.body
    assert msg.folder == "inbox"
    assert msg.email_id == "1"


def test_fetch_unread_without_since_days_only_searches_unseen():
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"])
    assert fake.last_search == ("UNSEEN",)


def test_fetch_unread_with_since_days_adds_since_criterion():
    import re
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"], since_days=30)
    assert fake.last_search[0] == "UNSEEN"
    assert fake.last_search[1] == "SINCE"
    # IMAP date format: DD-Mon-YYYY, e.g. 10-Jun-2026
    assert re.match(r"^\d{2}-[A-Z][a-z]{2}-\d{4}$", fake.last_search[2])


def test_fetch_with_subject_adds_quoted_subject_criterion():
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"], subject="Last War")
    assert fake.last_search[0] == "UNSEEN"
    assert "SUBJECT" in fake.last_search
    i = fake.last_search.index("SUBJECT")
    # value must be quoted so multi-word subjects stay a single IMAP token
    assert fake.last_search[i + 1] == '"Last War"'


def test_fetch_all_when_unseen_only_false_and_no_since():
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"], unseen_only=False)
    assert fake.last_search == ("ALL",)


def test_fetch_with_since_but_not_unseen_omits_unseen_criterion():
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"], since_days=30, unseen_only=False)
    assert "UNSEEN" not in fake.last_search
    assert fake.last_search[0] == "SINCE"


def test_fetch_unread_uses_peek_to_not_mark_seen():
    fake = FakeIMAP()
    _client_with(fake).fetch_unread(["inbox"])
    # Must PEEK so merely reading an email never sets the \\Seen flag.
    assert "PEEK" in fake.last_fetch_parts
    assert "RFC822" not in fake.last_fetch_parts


def test_fetch_unread_requires_connection():
    try:
        EmailClient(config=None).fetch_unread(["inbox"])
        assert False, "expected IMAPConnectionError"
    except IMAPConnectionError:
        pass


def test_mark_seen_sets_seen_flag():
    fake = FakeIMAP()
    client = _client_with(fake)
    client.mark_seen("1", "inbox")
    assert fake.stored == [("1", "+FLAGS", "\\Seen")]
