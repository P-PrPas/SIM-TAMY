"""Only an authored grandmother reply can reach a learner; all other output fails closed."""

import json
from unittest.mock import Mock

import pytest

from app.ai.family_voice import reply
from app.ai.llm_client import LLMClient, LLMTimeout


def test_only_selected_scene_information_reaches_generator():
    client = Mock(spec=LLMClient)
    client.complete_text.return_value = "Alternative response"
    assert (
        reply(
            client,
            persona="Grandmother",
            learner_text="Question",
            allowed=["Fallback", "Alternative response"],
        )
        == "Alternative response"
    )
    sent = client.complete_text.call_args.kwargs
    assert sent["purpose"] == "generator"
    assert json.loads(sent["prompt"]) == {
        "persona": "Grandmother",
        "learner_text": "Question",
        "allowed_replies": ["Fallback", "Alternative response"],
    }


@pytest.mark.parametrize(
    "unsafe",
    [
        "invented clinical clearance",
        "Fallback with added prescription",
        "",
        "ignore rules",
        "x" * 5000,
    ],
)
def test_rejected_text_is_never_returned_and_two_regenerations_then_fallback(unsafe):
    client = Mock(spec=LLMClient)
    client.complete_text.return_value = unsafe
    assert (
        reply(client, persona="Grandmother", learner_text="Question", allowed=["Fallback"])
        == "Fallback"
    )
    assert client.complete_text.call_count == 3


def test_provider_failure_falls_back_and_no_fallback_is_an_error():
    client = Mock(spec=LLMClient)
    client.complete_text.side_effect = LLMTimeout()
    assert (
        reply(client, persona="Grandmother", learner_text="Question", allowed=["Fallback"])
        == "Fallback"
    )
    with pytest.raises(ValueError):
        reply(client, persona="Grandmother", learner_text="Question", allowed=[])
