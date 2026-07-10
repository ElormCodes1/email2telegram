import logging
import signal
import sys
import time
from typing import List

from config import Config
from email_client import EmailClient, IMAPConnectionError
from filters import EmailFilter
from formatter import MessageFormatter
from logger import setup_logging
from telegram_client import TelegramClient


class EmailMonitor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._shutdown_requested = False
        self._folders = [f.strip() for f in config.imap_folders.split(",") if f.strip()]
        self._loop_count = 0
        self._last_health_check = 0

        self.email_client = EmailClient(config)
        self.telegram_client = TelegramClient(
            bot_token=config.telegram_bot_token.get_secret_value(),
            chat_id=config.telegram_chat_id,
        )
        self.filter = EmailFilter(
            subject_substring=config.filter_subject,
            body_substring=config.filter_body,
        )
        self.formatter = MessageFormatter()

    def _handle_signal(self, signum: int, frame) -> None:
        self._shutdown_requested = True

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        setup_logging(self.config.log_level)
        logging.info("Starting Email to Telegram monitor...")

        try:
            self.email_client.connect()
        except Exception as exc:
            logging.error("Could not connect to email server: %s", exc)
            sys.exit(1)

        try:
            while not self._shutdown_requested:
                self._loop_count += 1
                self._check_once()
                self._maybe_health_check()
                if not self._shutdown_requested:
                    logging.info("Waiting %s seconds before next check...", self.config.check_interval_seconds)
                    time.sleep(self.config.check_interval_seconds)
        finally:
            self.email_client.close()
            logging.info("Shutdown complete.")

    def _maybe_health_check(self) -> None:
        if self.config.health_check_interval_seconds <= 0:
            return

        now = time.time()
        if now - self._last_health_check < self.config.health_check_interval_seconds:
            return

        self._last_health_check = now
        logging.info("Health check: monitor is alive (loops=%s)", self._loop_count)

        if self.config.health_check_telegram:
            try:
                self.telegram_client.send("✅ Email2Telegram monitor is alive.")
            except Exception as exc:
                logging.error("Health check Telegram notification failed: %s", exc)

    def _check_once(self) -> None:
        # Ensure connection is alive before fetching. If not, reconnect.
        if not self.email_client.is_connected():
            logging.warning("IMAP connection lost or stale. Reconnecting...")
            try:
                self.email_client.reconnect()
            except Exception as exc:
                logging.error("Failed to reconnect to email server: %s", exc)
                return

        try:
            emails = self.email_client.fetch_unread(
                self._folders,
                since_days=self.config.search_since_days,
                subject=self.config.filter_subject,
            )
        except IMAPConnectionError as exc:
            logging.error("IMAP connection error during fetch: %s", exc)
            return
        except Exception as exc:
            logging.error("Unexpected error fetching emails: %s", exc)
            return

        for email in emails:
            try:
                logging.info("Checking email from %s | Subject: %s", email.sender, email.subject)

                if self.filter.matches(email):
                    logging.info("Email matches filter! Forwarding to Telegram...")
                    message = self.formatter.format(email)
                    self.telegram_client.send(message)
                    self.email_client.mark_seen(email.email_id, email.folder)
                else:
                    logging.info("Email does not meet filter criteria. Skipping.")
            except Exception as exc:
                logging.error("Error processing email from %s: %s", email.sender, exc)


def main() -> None:
    config = Config()
    monitor = EmailMonitor(config)
    monitor.run()


if __name__ == "__main__":
    main()
