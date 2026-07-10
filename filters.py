from email_client import EmailMessage


class EmailFilter:
    def __init__(self, subject_substring: str, body_substring: str) -> None:
        self._subject = subject_substring.lower()
        self._body = body_substring.lower()

    def matches(self, email: EmailMessage) -> bool:
        subject_match = self._subject in email.subject.lower() if self._subject else True
        body_match = self._body in email.body.lower() if self._body else True
        return subject_match and body_match
