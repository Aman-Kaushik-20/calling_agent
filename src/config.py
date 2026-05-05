from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# Pydantic BaseSettings instance for storing secrets from .env.
# All notification-provider settings are optional — a provider is silently
# disabled if its required vars are missing.
class Settings(BaseSettings):
    # ─── Bolna ───────────────────────────────────────────────────────────────
    bolna_api_key: str
    bolna_base_url: str = "https://api.bolna.ai"

    # ─── Slack ───────────────────────────────────────────────────────────────
    slack_bot_token: Optional[str] = None
    slack_base_url: str = "https://slack.com/api"
    slack_alert_channel: Optional[str] = None

    # ─── Discord ─────────────────────────────────────────────────────────────
    discord_webhook_url: Optional[str] = None

    # ─── Mattermost ──────────────────────────────────────────────────────────
    # Slack-compatible payload shape — points at any incoming-webhook URL.
    mattermost_webhook_url: Optional[str] = None

    # ─── ClickUp ─────────────────────────────────────────────────────────────
    # Posts a comment on the configured task whenever a Bolna call ends.
    clickup_api_token: Optional[str] = None
    clickup_task_id: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
