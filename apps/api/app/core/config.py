from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment config (PRD 6.5). Secrets are SecretStr so they never print."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    database_url: str = "postgresql+psycopg://sim:sim@localhost:5432/simtamy"
    llm_provider: str = "mock"
    llm_api_key: SecretStr | None = None
    llm_model_interpreter: str | None = None
    llm_model_generator: str | None = None
    llm_model_debrief: str | None = None
    llm_timeout_s: int = 15
    llm_base_url: str | None = None  # openai_like provider, e.g. https://api.z.ai/api/paas/v4
    llm_reasoning_effort: str | None = None  # passed through when set (GLM-5.3: low|high|max)
    mock_llm_script: Path | None = None  # YAML script for the mock provider
    instructor_secret: SecretStr | None = None
    content_dir: Path = Path("./content")
    allow_draft_cases: bool = True
    glass_box_live: bool = False
    log_retention_days: int = 30
    cors_origins: str = ""  # comma-separated

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
