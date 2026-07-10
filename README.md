# 📧 Email2Telegram

> Because checking your work email for a game OTP is *not* fun.

## What is this?

Email2Telegram is a tiny Python bot that sits on a server, watches your email inbox (and spam folder), and forwards matching emails straight to your Telegram. That's it. No fancy dashboard, no bloat — just set your filters and forget it exists.

## Why I made this

Here's the thing: I play [Last War](https://lastwar.com) (yeah, the mobile strategy game). Every time I log in, it sends an OTP to my email. The problem? That email account is **separate** from everything else. I already have work email, personal email, side project emails — the whole nine yards — all logged in on my phone. Adding *another* email account **just for game OTPs** felt completely unnecessary. Why clutter my phone with yet another email app login for something I only need for a 6-digit code?

Meanwhile, I'm already on **Telegram** all day. So I thought... why not just pipe the OTP emails into Telegram instead? This bot does exactly that. Now I get my login codes instantly in a Telegram chat without ever touching that email app.

## How it works

1. **Connects to your IMAP server** — checks the configured folders every X seconds
2. **Filters unread emails** — only forwards emails whose subject AND body contain your configured keywords
3. **Formats & sends to Telegram** — strips HTML, escapes entities, truncates long bodies, and delivers a clean message via your bot
4. **Marks emails as read** — so you don't get spammed with duplicates
5. **Auto-reconnects** — if the IMAP connection goes stale (server-side timeout), it reconnects automatically

The bot runs as a simple loop. If it crashes, it restarts. If you hit `Ctrl+C`, it shuts down gracefully.

## Setup

### 1. Install deps

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in your stuff:

```env
EMAIL_ADDRESS=youremail@example.com
EMAIL_PASSWORD=your_app_password
IMAP_SERVER=imap.example.com
IMAP_PORT=993

TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890

FILTER_SUBJECT=Last War
FILTER_BODY=Login

IMAP_FOLDERS=inbox,Spam,Notification

CHECK_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
HEALTH_CHECK_INTERVAL_SECONDS=3600
HEALTH_CHECK_TELEGRAM=false
```

- `IMAP_FOLDERS` — comma-separated list of folders to watch. Case-sensitive on some servers; `INBOX` is the RFC-standard name.
- `HEALTH_CHECK_INTERVAL_SECONDS` — log heartbeat every N seconds. Set to `0` to disable.
- `HEALTH_CHECK_TELEGRAM` — set to `true` to also get a Telegram message on each health check.

**Tips:**
- Use an **app-specific password** (not your main password) if your provider supports it
- Get your `TELEGRAM_CHAT_ID` by messaging `@userinfobot` on Telegram
- `FILTER_SUBJECT` and `FILTER_BODY` are **case-insensitive** substrings — leave empty to match everything

### 3. Run it

```bash
python3 email2telegram.py
```

Or use the systemd service:

```bash
sudo cp email2telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now email2telegram
sudo journalctl -u email-telegram-bot -f
```

## Project Structure

```
email2telegram/
├── email2telegram.py       # Main loop & orchestrator
├── config.py               # .env loader with Pydantic validation
├── email_client.py         # IMAP stuff — fetch, parse, mark read, reconnect
├── telegram_client.py      # Telegram API sender with retry
├── filters.py              # Does this email match? (yes/no)
├── formatter.py            # Cleans up HTML for Telegram
├── logger.py               # Logging setup
├── email2telegram.service  # systemd unit file
├── requirements.txt
└── .env.example
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

8 tests covering email filtering and message formatting. Easy to extend if you want to add more.

## Known Limitations / TODOs

- Only handles `text/plain` and basic `text/html` emails (attachments are ignored)
- HTML tag stripping is regex-based, not a full parser — might munch text with lots of `<` `>` symbols
- Folder names are configurable, but some providers use unexpected names for Spam/Junk

## License

Do whatever you want. If this saves you from installing yet another email app on your phone, my job here is done. 🎮
