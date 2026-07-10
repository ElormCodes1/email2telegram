import imaplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from email import message_from_bytes
from typing import List, Optional


@dataclass
class EmailMessage:
    subject: str
    sender: str
    body: str
    folder: str
    email_id: str


def _decode_subject(subject_header: Optional[str]) -> str:
    if not subject_header:
        return ""
    decoded_fragments = decode_header(subject_header)
    subject = ""
    for content, encoding in decoded_fragments:
        if isinstance(content, bytes):
            try:
                subject += content.decode(encoding or "utf-8", errors="replace")
            except LookupError:
                subject += content.decode("utf-8", errors="replace")
        else:
            subject += content
    return subject


def _extract_body(msg: Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="replace")
    else:
        content_type = msg.get_content_type()
        if content_type in ("text/plain", "text/html"):
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
    return body


class IMAPConnectionError(Exception):
    pass


class EmailClient:
    def __init__(self, config) -> None:
        self.config = config
        self._mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        try:
            self._mail = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            self._mail.login(self.config.email_address, self.config.email_password.get_secret_value())
        except Exception as exc:
            raise IMAPConnectionError(f"Failed to connect/login to IMAP: {exc}") from exc

    def is_connected(self) -> bool:
        """Check if the IMAP connection is still alive via NOOP."""
        if self._mail is None:
            return False
        try:
            status, _ = self._mail.noop()
            return status == "OK"
        except Exception:
            return False

    def reconnect(self) -> None:
        """Close stale connection and reconnect."""
        self.close()
        self.connect()

    def fetch_unread(
        self,
        folders: List[str],
        since_days: Optional[int] = None,
        unseen_only: bool = True,
        subject: Optional[str] = None,
    ) -> List[EmailMessage]:
        messages: List[EmailMessage] = []
        if self._mail is None:
            raise IMAPConnectionError("Not connected. Call connect() first.")

        # Build server-side search criteria so the IMAP server does the filtering
        # and we only download matching messages. UNSEEN limits to unread mail;
        # SINCE filters by received date (IMAP wants DD-Mon-YYYY, e.g. 10-Jun-2026);
        # SUBJECT is a case-insensitive substring match on the subject header.
        # With no criteria at all, fall back to ALL.
        criteria: List[str] = []
        if unseen_only:
            criteria.append("UNSEEN")
        if since_days and since_days > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%d-%b-%Y")
            criteria += ["SINCE", cutoff]
        if subject:
            # Quote the value so subjects containing spaces are a single IMAP token.
            escaped = subject.replace("\\", "\\\\").replace('"', '\\"')
            criteria += ["SUBJECT", f'"{escaped}"']
        if not criteria:
            criteria = ["ALL"]

        for folder in folders:
            try:
                status, _ = self._mail.select(folder)
                if status != "OK":
                    continue
            except Exception as exc:
                raise IMAPConnectionError(f"Failed to select folder {folder}: {exc}") from exc

            status, data = self._mail.search(None, *criteria)
            if status != "OK" or not data or not data[0]:
                continue

            for email_id in data[0].split():
                # BODY.PEEK[] fetches the full message WITHOUT setting the \Seen
                # flag, so reading an email never marks it as read. Only mark_seen()
                # (called after a successful forward) flags a message as seen.
                res, msg_data = self._mail.fetch(email_id, "(BODY.PEEK[])")
                if res != "OK" or not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                    continue

                raw_email = msg_data[0][1]
                if not isinstance(raw_email, bytes):
                    continue

                msg = message_from_bytes(raw_email)
                subject = _decode_subject(msg.get("Subject"))
                sender = str(msg.get("From", ""))
                body = _extract_body(msg)
                messages.append(EmailMessage(subject=subject, sender=sender, body=body, folder=folder, email_id=email_id.decode()))

        return messages

    def mark_seen(self, email_id: str, folder: str) -> None:
        if self._mail is not None:
            try:
                self._mail.select(folder)
                self._mail.store(email_id, "+FLAGS", "\\Seen")
            except Exception:
                pass

    def close(self) -> None:
        if self._mail is not None:
            try:
                self._mail.close()
                self._mail.logout()
            except Exception:
                pass
            finally:
                self._mail = None
