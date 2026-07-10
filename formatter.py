import html
import re
from email_client import EmailMessage


class MessageFormatter:
    def __init__(self, max_length: int = 1000) -> None:
        self._max_length = max_length

    def format(self, email: EmailMessage) -> str:
        body_text = re.sub(r"<br\s*/?>", "\n", email.body, flags=re.IGNORECASE)
        body_text = re.sub(r"</?[a-zA-Z][^>]*>", "", body_text)
        body_text = html.escape(body_text.strip())

        snippet = body_text[: self._max_length]
        if len(body_text) > self._max_length:
            snippet += "..."

        return (
            f"📧 <b>New Match Email (Folder: {html.escape(email.folder)})</b>\n\n"
            f"<b>From:</b> {html.escape(email.sender)}\n"
            f"<b>Subject:</b> {html.escape(email.subject)}\n"
            f"<b>Body:</b>\n{snippet}"
        )
