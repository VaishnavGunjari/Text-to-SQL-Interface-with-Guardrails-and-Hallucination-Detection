from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATHS = (
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent / ".env",
    ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str
    database_readonly_url: str = ""

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    llm_provider: str = "auto"
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    max_rows: int = 1000
    query_timeout_seconds: int = 30
    max_subquery_depth: int = 3
    max_estimated_scan_rows: int = 1000000
    enable_multi_query_validation: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def readonly_url(self) -> str:
        url = self.database_readonly_url or self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
