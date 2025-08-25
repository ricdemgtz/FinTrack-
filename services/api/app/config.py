from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = "sqlite:///./fintrack.db"
    enable_notion: bool = False
    notion_token: str | None = None
    notion_database_id: str | None = None
    webhook_secret: str = "changeme"


settings = Settings()
