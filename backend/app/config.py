"""설정 모듈 — 환경변수 로드"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    kiwoom_app_key: str = ""
    kiwoom_secret_key: str = ""
    kiwoom_api_url: str = "https://api.kiwoom.com"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    database_url: str = "sqlite+aiosqlite:///./watchlist.db"
    watch_days: int = 5
    target_rate: float = 50.0
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
