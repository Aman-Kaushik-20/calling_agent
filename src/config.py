from pydantic_settings import BaseSettings, SettingsConfigDict

# Pydantic BaseSettings Instance for storing Secrets from .env
class Settings(BaseSettings):
    bolna_api_key: str
    bolna_base_url: str = "https://api.bolna.ai"

    slack_bot_token: str
    slack_base_url: str = "https://slack.com/api"
    slack_alert_channel: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
