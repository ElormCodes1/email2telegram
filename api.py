"""Read-only HTTP API for querying matching emails.

GET /emails?days_since=30&filter_subject=...&filter_body=...
Returns unread emails (received within `days_since` days) whose subject and
body contain the given substrings. Fetching uses IMAP BODY.PEEK[], so querying
never marks mail as read.

Run with:  uvicorn api:app --reload
"""
from typing import List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from config import Config
from email_client import EmailClient, IMAPConnectionError
from filters import EmailFilter
from formatter import MessageFormatter

app = FastAPI(title="Email2Telegram API")


class EmailsResponse(BaseModel):
    count: int
    emails: List[str]


@app.get("/")
def root() -> dict:
    return {
        "service": "email2telegram-api",
        "status": "ok",
        "endpoints": {"emails": "/emails", "health": "/health", "docs": "/docs"},
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/emails", response_model=EmailsResponse)
def get_emails(
    days_since: int = Query(30, ge=0, description="Only emails received within this many days (0 = no limit)"),
    filter_subject: str = Query("", description="Substring that must appear in the subject (case-insensitive)"),
    filter_body: str = Query("", description="Substring that must appear in the body (case-insensitive)"),
    unread_only: bool = Query(False, description="If true, only return unread (UNSEEN) emails"),
) -> EmailsResponse:
    config = Config()
    folders = [f.strip() for f in config.imap_folders.split(",") if f.strip()]

    client = EmailClient(config)
    try:
        client.connect()
        emails = client.fetch_unread(
            folders,
            since_days=days_since,
            unseen_only=unread_only,
            subject=filter_subject,
        )
    except IMAPConnectionError as exc:
        raise HTTPException(status_code=502, detail=f"IMAP error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
    finally:
        client.close()

    email_filter = EmailFilter(filter_subject, filter_body)
    formatter = MessageFormatter()
    matched = [e for e in emails if email_filter.matches(e)]

    return EmailsResponse(
        count=len(matched),
        emails=[formatter.to_text(e) for e in matched],
    )
