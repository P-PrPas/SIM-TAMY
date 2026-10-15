"""Configuration contract for the interpreter confidence policy (T-031)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_confidence_thresholds_have_the_prd_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.action_accept_threshold == 0.75
    assert settings.action_clarify_threshold == 0.5


def test_confidence_thresholds_can_be_configured() -> None:
    settings = Settings(_env_file=None, action_accept_threshold=0.9, action_clarify_threshold=0.65)

    assert (settings.action_accept_threshold, settings.action_clarify_threshold) == (0.9, 0.65)


@pytest.mark.parametrize(
    ("accept", "clarify"),
    [(0.5, 0.5), (0.4, 0.5), (1.1, 0.5), (0.75, -0.1)],
)
def test_invalid_confidence_thresholds_fail_fast(accept: float, clarify: float) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            action_accept_threshold=accept,
            action_clarify_threshold=clarify,
        )
