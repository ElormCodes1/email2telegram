import html
import re
from email_client import EmailMessage


class MessageFormatter:
    def __init__(self, max_length: int = 1000) -> None:
        self._max_length = max_length

    def _clean_body(self, body: str) -> str:
        """Strip HTML down to plain text and truncate to max_length."""
        body_text = re.sub(r"<br\s*/?>", "\n", body, flags=re.IGNORECASE)
        body_text = re.sub(r"</?[a-zA-Z][^>]*>", "", body_text)
        body_text = body_text.strip()

        snippet = body_text[: self._max_length]
        if len(body_text) > self._max_length:
            snippet += "..."
        return snippet

    def format(self, email: EmailMessage) -> str:
        """HTML-formatted message for Telegram (parse_mode=HTML)."""
        snippet = html.escape(self._clean_body(email.body))
        return (
            f"📧 <b>New Match Email (Folder: {html.escape(email.folder)})</b>\n\n"
            f"<b>From:</b> {html.escape(email.sender)}\n"
            f"<b>Subject:</b> {html.escape(email.subject)}\n"
            f"<b>Body:</b>\n{snippet}"
        )

    def to_text(self, email: EmailMessage) -> str:
        """Plain-text rendering: parsed From/Subject/Body, no HTML."""
        return (
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Body:\n{self._clean_body(email.body)}"
        )
