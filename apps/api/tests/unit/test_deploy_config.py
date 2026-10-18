"""T-090/T-093: what a PaaS hands us (DATABASE_URL, web origins) is accepted as is."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app

PROD = "https://sim-tamy.vercel.app"
PREVIEW = "https://sim-tamy-git-feat-x-team.vercel.app"


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def allowed_origin(origin: str) -> str | None:
    """The `Access-Control-Allow-Origin` a browser preflight from `origin` would get."""
    get_settings.cache_clear()
    r = TestClient(create_app()).options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    return r.headers.get("access-control-allow-origin")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_database_url_always_uses_the_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


def test_exact_origin_regex_origin_and_strangers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", PROD)
    monkeypatch.setenv("CORS_ORIGIN_REGEX", r"https://sim-tamy-.*-team\.vercel\.app")

    assert allowed_origin(PROD) == PROD
    assert allowed_origin(PREVIEW) == PREVIEW
    assert allowed_origin("https://evil.example") is None
    assert allowed_origin(PREVIEW + ".evil.example") is None  # the whole origin must match


def test_no_cors_headers_when_nothing_is_configured() -> None:
    assert allowed_origin(PROD) is None


def test_compose_passes_the_confidence_thresholds_with_the_code_defaults() -> None:
    """A Settings field that compose does not forward is silently ignored inside the container."""
    import yaml

    compose = yaml.safe_load(
        (Path(__file__).resolve().parents[4] / "docker-compose.yml").read_text()
    )
    env = compose["services"]["api"]["environment"]
    defaults = Settings()
    assert (
        env["ACTION_ACCEPT_THRESHOLD"]
        == f"${{ACTION_ACCEPT_THRESHOLD:-{defaults.action_accept_threshold}}}"
    )
    assert (
        env["ACTION_CLARIFY_THRESHOLD"]
        == f"${{ACTION_CLARIFY_THRESHOLD:-{defaults.action_clarify_threshold}}}"
    )


def test_the_image_migrates_on_start_and_does_not_run_as_root() -> None:
    """Compose and Render both start the same image from an empty database (T-091)."""
    import yaml

    root = Path(__file__).resolve().parents[4]
    dockerfile = (root / "apps/api/Dockerfile").read_text()
    cmd = dockerfile[dockerfile.rindex("CMD ") :]
    render = yaml.safe_load((root / "render.yaml").read_text())["services"][0]

    assert "python -m app.db.migrate && exec uvicorn" in cmd and "${PORT:-8000}" in cmd
    assert "\nUSER app\n" in dockerfile and "HEALTHCHECK" in dockerfile
    assert "dockerCommand" not in render  # one start command, the image's
    assert render["healthCheckPath"] == "/health" and render["autoDeployTrigger"] == "checksPass"


def test_compose_forwards_every_llm_setting() -> None:
    """GLM needs LLM_BASE_URL and LLM_REASONING_EFFORT; a line compose omits is silently ignored."""
    import yaml

    root = Path(__file__).resolve().parents[4]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    wanted = {name.upper() for name in Settings.model_fields if name.startswith("llm_")}

    assert wanted <= set(compose["services"]["api"]["environment"])


def test_env_example_has_no_trailing_comments() -> None:
    """docker compose reads `KEY=value  # note` with the note as part of the value."""
    root = Path(__file__).resolve().parents[4]
    lines = (root / ".env.example").read_text().splitlines()
    assert [ln for ln in lines if ln and not ln.startswith("#") and " #" in ln] == []


def test_render_preserves_the_operator_selected_llm_provider() -> None:
    """Blueprint sync must not overwrite a working live provider with the demo default."""
    import yaml

    root = Path(__file__).resolve().parents[4]
    service = yaml.safe_load((root / "render.yaml").read_text())["services"][0]
    provider = next(item for item in service["envVars"] if item.get("key") == "LLM_PROVIDER")
    assert provider == {"key": "LLM_PROVIDER", "sync": False}
