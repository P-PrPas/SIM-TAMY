from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
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
    action_accept_threshold: float = Field(default=0.75, ge=0, le=1, allow_inf_nan=False)
    action_clarify_threshold: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    llm_base_url: str | None = None  # openai_like provider, e.g. https://api.z.ai/api/paas/v4
    llm_reasoning_effort: str | None = None  # passed through when set (GLM-5.3: low|high|max)
    mock_llm_script: Path | None = None  # YAML script for the mock provider
    instructor_secret: SecretStr | None = None
    content_dir: Path = Path("./content")
    allow_draft_cases: bool = True
    glass_box_live: bool = False
    log_retention_days: int = 30
    cors_origins: str = ""  # comma-separated
    cors_origin_regex: str | None = None  # e.g. Vercel previews; matched against the whole origin

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, url: str) -> str:
        """Hosts hand out `postgres://` / `postgresql://`; SQLAlchemy would pick psycopg2."""
        for plain in ("postgres://", "postgresql://"):
            if url.startswith(plain):
                return "postgresql+psycopg://" + url[len(plain) :]
        return url

    @model_validator(mode="after")
    def valid_confidence_band(self) -> Self:
        if self.action_clarify_threshold >= self.action_accept_threshold:
            raise ValueError("ACTION_CLARIFY_THRESHOLD must be below ACTION_ACCEPT_THRESHOLD")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
