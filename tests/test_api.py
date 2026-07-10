import pytest
from fastapi.testclient import TestClient

import api
from email_client import EmailMessage, IMAPConnectionError


class FakeConfig:
    imap_folders = "inbox,Spam"


class FakeClient:
    """Stand-in for EmailClient. Records the since_days it was called with."""

    last_since = None
    last_unseen_only = None
    last_subject = None
    fail = False
    emails = []

    def __init__(self, config):
        pass

    def connect(self):
        if FakeClient.fail:
            raise IMAPConnectionError("boom")

    def fetch_unread(self, folders, since_days=None, unseen_only=True, subject=None):
        FakeClient.last_since = since_days
        FakeClient.last_unseen_only = unseen_only
        FakeClient.last_subject = subject
        return FakeClient.emails

    def close(self):
        pass


@pytest.fixture(autouse=True)
def patch_deps(monkeypatch):
    monkeypatch.setattr(api, "Config", FakeConfig)
    monkeypatch.setattr(api, "EmailClient", FakeClient)
    FakeClient.last_since = None
    FakeClient.fail = False
    FakeClient.emails = [
        EmailMessage(subject="[Last War] Account Sign In", sender="a@b.com", body="verify your Email", folder="inbox", email_id="1"),
        EmailMessage(subject="Newsletter", sender="n@b.com", body="nothing relevant", folder="inbox", email_id="2"),
    ]
    yield


client = TestClient(api.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_filters_return_only_matching_and_pass_days_since():
    r = client.get("/emails", params={"days_since": 15, "filter_subject": "Last War", "filter_body": "Email"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    # response items are parsed plain-text blocks (From/Subject/Body)
    text = data["emails"][0]
    assert text.startswith("From: a@b.com")
    assert "Subject: [Last War] Account Sign In" in text
    assert "Body:\nverify your Email" in text
    assert FakeClient.last_since == 15
    # subject is pushed to the IMAP search so only matching mail is downloaded
    assert FakeClient.last_subject == "Last War"


def test_empty_filters_return_all():
    r = client.get("/emails")
    data = r.json()
    assert data["count"] == 2
    # default days_since is 30
    assert FakeClient.last_since == 30
    # by default the API searches ALL mail, not just unread
    assert FakeClient.last_unseen_only is False


def test_unread_only_flag_is_passed_through():
    client.get("/emails", params={"unread_only": "true"})
    assert FakeClient.last_unseen_only is True


def test_no_match_returns_empty_list():
    r = client.get("/emails", params={"filter_subject": "does-not-exist"})
    data = r.json()
    assert data["count"] == 0
    assert data["emails"] == []


def test_negative_days_since_is_rejected():
    r = client.get("/emails", params={"days_since": -5})
    assert r.status_code == 422  # FastAPI validation (ge=0)


def test_imap_error_returns_502():
    FakeClient.fail = True
    r = client.get("/emails")
    assert r.status_code == 502
    assert "IMAP error" in r.json()["detail"]
