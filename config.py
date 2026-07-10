from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    email_address: str
    email_password: SecretStr
    imap_server: str
    imap_port: int = 993

    telegram_bot_token: SecretStr
    telegram_chat_id: str

    filter_subject: str = ""
    filter_body: str = ""

    imap_folders: str = "inbox,Spam"

    # Only search unread emails received within this many days. 0 disables the limit.
    search_since_days: int = 30

    check_interval_seconds: int = 30
    log_level: str = "INFO"
    health_check_interval_seconds: int = 3600
    health_check_telegram: bool = False
