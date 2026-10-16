"""T-035: format engine findings via LLM, with a deterministic, claim-safe fallback."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.ai.llm_client import LLMClient, LLMError
from app.api.v1.schemas import Debrief, DebriefParagraph
from app.domain.scoring import Finding

_PROMPTS = Path(__file__).resolve().parent / "prompts"


class _Paragraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_ids: list[str]
    text_th: str


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphs: list[_Paragraph]


def _template(findings: tuple[Finding, ...]) -> Debrief:
    return Debrief(
        source="template",
        paragraphs=[
            DebriefParagraph(finding_ids=[finding.id], text_th=finding.text_th)
            for finding in findings
        ],
    )


def _valid(raw: _Output, findings: tuple[Finding, ...]) -> bool:
    by_id = {finding.id: finding for finding in findings}
    ids = [id_ for paragraph in raw.paragraphs for id_ in paragraph.finding_ids]
    if len(ids) != len(findings) or set(ids) != set(by_id):
        return False
    for paragraph in raw.paragraphs:
        if not paragraph.finding_ids:
            return False
        # Exact source wording is intentional: no hallucinated fact, reference, or score can pass.
        expected = " ".join(by_id[id_].text_th.strip() for id_ in paragraph.finding_ids)
        if paragraph.text_th.strip() != expected:
            return False
    return True


def generate_debrief(client: LLMClient, findings: tuple[Finding, ...]) -> Debrief:
    if not findings:
        return _template(findings)
    payload = [
        {"id": finding.id, "polarity": finding.polarity, "text_th": finding.text_th}
        for finding in findings
    ]
    template = (_PROMPTS / "debrief_input.md").read_text(encoding="utf-8")
    prompt = template.replace("{findings_json}", json.dumps(payload, ensure_ascii=False))
    system = (_PROMPTS / "debrief.md").read_text(encoding="utf-8")
    try:
        raw = client.complete_structured(
            _Output,
            purpose="debrief",
            system=system,
            prompt=prompt,
            temperature=0.3,
            max_tokens=1200,
        )
    except LLMError:
        return _template(findings)
    if not _valid(raw, findings):
        return _template(findings)
    return Debrief(
        source="llm",
        paragraphs=[DebriefParagraph.model_validate(p.model_dump()) for p in raw.paragraphs],
    )
