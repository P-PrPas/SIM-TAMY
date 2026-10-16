"""T-035: LLM wording cannot add findings, claims, scores, or references."""

import pytest

from app.ai.debrief import generate_debrief
from app.ai.llm_client import LLMClient
from app.ai.providers.mock import MockProvider
from app.domain.scoring import Finding


@pytest.fixture
def findings() -> tuple[Finding, ...]:
    return (
        Finding(
            id="F1",
            polarity="strength",
            rubric_item_id="R1",
            text_th="Source A",
            evidence_refs=(1,),
            reference_ids=(),
        ),
        Finding(
            id="F2",
            polarity="improve",
            rubric_item_id="R2",
            text_th="Source B",
            evidence_refs=(2,),
            reference_ids=(),
        ),
    )


def client(reply: object) -> LLMClient:
    return LLMClient(MockProvider({"debrief": [{"default": reply}]}), model="mock", timeout_s=1)


def test_debrief_accepts_only_complete_exact_source_wording(findings):
    result = generate_debrief(
        client({"paragraphs": [{"finding_ids": ["F1", "F2"], "text_th": "Source A Source B"}]}),
        findings,
    )
    assert result.source == "llm"
    assert [p.finding_ids for p in result.paragraphs] == [["F1", "F2"]]


@pytest.mark.parametrize(
    "reply",
    [
        {"paragraphs": [{"finding_ids": ["F1"], "text_th": "Source A"}]},
        {"paragraphs": [{"finding_ids": ["F1", "F3"], "text_th": "Source A Other"}]},
        {
            "paragraphs": [
                {"finding_ids": ["F1", "F1", "F2"], "text_th": "Source A Source A Source B"}
            ]
        },
        {"paragraphs": [{"finding_ids": ["F1", "F2"], "text_th": "Source A Source B 99%"}]},
        {"paragraphs": [{"finding_ids": ["F1", "F2"], "text_th": "Invented claim"}]},
    ],
)
def test_debrief_rejects_missing_unknown_duplicate_or_invented_material(findings, reply):
    result = generate_debrief(client(reply), findings)
    assert result.source == "template"
    assert [p.text_th for p in result.paragraphs] == ["Source A", "Source B"]


def test_debrief_falls_back_when_provider_fails(findings):
    result = generate_debrief(LLMClient(MockProvider(), model="mock", timeout_s=1), findings)
    assert result.source == "template"


def test_empty_findings_do_not_call_llm():
    class NeverCall:
        def complete_structured(self, *args, **kwargs):
            raise AssertionError("LLM should not be called")

    result = generate_debrief(NeverCall(), ())  # type: ignore[arg-type]
    assert result.source == "template" and result.paragraphs == []
