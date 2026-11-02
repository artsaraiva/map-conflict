from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/geopolitics"
    )
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    # Shared secret for POST /api/pipeline/trigger; empty turns the endpoint off
    pipeline_trigger_secret: str = ""

    # Scraping config
    scrape_interval_minutes: int = 15
    max_articles_per_feed: int = 20

    # Telegram config
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_session: str = ""
    telegram_channels: str = (
        "FrontlineReportNews,BellumActaNews,rnintel,tglobaleye,tupireport,disclosetv"
    )
    telegram_max_messages: int = 20
    telegram_media_dir: str = "/app/media/telegram"
    telegram_max_video_size_mb: int = 50

    class Config:
        env_file = "../.env", ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
