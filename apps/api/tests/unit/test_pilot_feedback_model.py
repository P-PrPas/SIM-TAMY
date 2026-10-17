"""Pilot input boundaries; feedback is not a clinical or scoring signal."""

import pytest
from pydantic import ValidationError

from app.api.v1.schemas import PilotFeedbackRequest

BASE = dict(role="learner", usefulness=4, realism=3, comment="Synthetic feedback", consent=True)


@pytest.mark.parametrize(
    "change",
    [
        dict(consent=False),
        dict(role="verified_expert"),
        dict(usefulness=0),
        dict(realism=6),
        dict(usefulness=True),
        dict(comment="x" * 501),
    ],
)
def test_invalid_feedback_is_rejected(change):
    with pytest.raises(ValidationError):
        PilotFeedbackRequest.model_validate({**BASE, **change})


def test_feedback_drops_control_characters():
    assert PilotFeedbackRequest.model_validate({**BASE, "comment": " x\x00 "}).comment == "x"
