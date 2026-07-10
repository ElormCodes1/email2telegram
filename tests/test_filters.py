from email_client import EmailMessage
from filters import EmailFilter


def test_match_when_both_substrings_present():
    email = EmailMessage(subject="[Last War] Account Sign In", sender="a@b.com", body="Verify your Email", folder="inbox", email_id="1")
    f = EmailFilter(subject_substring="Last War", body_substring="Email")
    assert f.matches(email) is True


def test_no_match_when_subject_missing():
    email = EmailMessage(subject="Hello", sender="a@b.com", body="Verify your Email", folder="inbox", email_id="1")
    f = EmailFilter(subject_substring="Last War", body_substring="Email")
    assert f.matches(email) is False


def test_no_match_when_body_missing():
    email = EmailMessage(subject="[Last War] Account Sign In", sender="a@b.com", body="Hello", folder="inbox", email_id="1")
    f = EmailFilter(subject_substring="Last War", body_substring="Email")
    assert f.matches(email) is False


def test_empty_filter_matches_everything():
    email = EmailMessage(subject="Anything", sender="a@b.com", body="Anything", folder="inbox", email_id="1")
    f = EmailFilter(subject_substring="", body_substring="")
    assert f.matches(email) is True
