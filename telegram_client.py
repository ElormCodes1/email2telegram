import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential


class TelegramAPIError(Exception):
    pass


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._base_url = f"https://api.telegram.org/bot{self._token}"

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def send(self, message: str, parse_mode: Optional[str] = "HTML") -> None:
        url = f"{self._base_url}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": parse_mode or "",
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode())
                if not result.get("ok"):
                    raise TelegramAPIError(f"Telegram API error: {result}")
        except urllib.error.HTTPError as exc:
            raise TelegramAPIError(f"HTTP {exc.code}: {exc.reason}") from exc
        except Exception as exc:
            raise TelegramAPIError(f"Failed to send Telegram message: {exc}") from exc
