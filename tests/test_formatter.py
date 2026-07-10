from email_client import EmailMessage
from formatter import MessageFormatter


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
