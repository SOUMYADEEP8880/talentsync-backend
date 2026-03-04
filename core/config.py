from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "TalentSync AI"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./talentsync.db"

    # Anthropic (required)
    ANTHROPIC_API_KEY: str = ""

    # Pinecone (free tier — no OpenAI needed)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "talentsync-jobs"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
