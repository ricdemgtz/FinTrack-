from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = "sqlite:///./fintrack.db"
    enable_notion: bool = False
    notion_token: str | None = None
    notion_database_id: str | None = None

    # Redis configuration for rate limiting
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str | None = None

    # Rate limiting and logging
    rate_limit: str = "100/minute"
    log_level: str = "info"

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"


settings = Settings()
