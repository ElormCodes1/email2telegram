import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from telegram_client import TelegramClient, TelegramAPIError


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_send_builds_correct_url_and_payload():
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["data"] = req.data
        return _FakeResponse({"ok": True})

    client = TelegramClient(bot_token="TOKEN123", chat_id="999")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client.send("hello world")

    assert captured["url"] == "https://api.telegram.org/botTOKEN123/sendMessage"
    body = captured["data"].decode()
    assert "chat_id=999" in body
    assert "text=hello+world" in body
    assert "parse_mode=HTML" in body


def test_send_raises_when_api_returns_not_ok():
    client = TelegramClient(bot_token="T", chat_id="1")
    with patch("urllib.request.urlopen", return_value=_FakeResponse({"ok": False, "description": "bad"})):
        with pytest.raises(TelegramAPIError):
            client.send("hi")


def test_send_wraps_http_error_and_retries():
    calls = {"n": 0}

    def boom(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(b""))

    client = TelegramClient(bot_token="T", chat_id="1")
    with patch("urllib.request.urlopen", side_effect=boom):
        with pytest.raises(TelegramAPIError):
            client.send("hi")

    # tenacity retries up to 5 attempts before re-raising
    assert calls["n"] == 5
