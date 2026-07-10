from email_client import EmailMessage
from formatter import MessageFormatter


def test_to_text_parses_to_plain_from_subject_body():
    email = EmailMessage(
        subject="Similarweb Account Login Verification",
        sender="Similarweb <noreply@similarweb.com>",
        body="Hey Elorm,<br/> please <a href='https://x.com/verify'>change your password</a>. Code: 117399",
        folder="inbox",
        email_id="1",
    )
    result = MessageFormatter().to_text(email)
    assert result.startswith("From: Similarweb <noreply@similarweb.com>\n")
    assert "Subject: Similarweb Account Login Verification\n" in result
    assert "Body:\n" in result
    # HTML is stripped: no tags, link text kept, plain (not escaped)
    assert "<a href=" not in result
    assert "<br" not in result
    assert "change your password" in result
    assert "Code: 117399" in result


def test_format_basic():
    email = EmailMessage(subject="Test", sender="a@b.com", body="Hello", folder="inbox", email_id="1")
    fmt = MessageFormatter(max_length=100)
    result = fmt.format(email)
    assert "Test" in result
    assert "a@b.com" in result
    assert "Hello" in result
    assert "inbox" in result


def test_truncates_long_body():
    email = EmailMessage(subject="S", sender="a@b.com", body="A" * 2000, folder="inbox", email_id="1")
    fmt = MessageFormatter(max_length=10)
    result = fmt.format(email)
    assert result.endswith("...")
    assert len(result) < 2000


def test_strips_html_tags():
    email = EmailMessage(subject="S", sender="a@b.com", body="<p>Hello</p><br/>World", folder="inbox", email_id="1")
    fmt = MessageFormatter(max_length=1000)
    result = fmt.format(email)
    assert "<p>" not in result
    assert "</p>" not in result
    assert "Hello" in result
    assert "World" in result


def test_escapes_html_entities():
    email = EmailMessage(subject="S", sender="a@b.com", body="5 < 10 & 10 > 5", folder="inbox", email_id="1")
    fmt = MessageFormatter(max_length=1000)
    result = fmt.format(email)
    assert "&lt;" in result
    assert "&gt;" in result
    assert "&amp;" in result
