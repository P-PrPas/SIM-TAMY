"""AI-03 (contracts section 5): debrief text from the finished, engine-scored report. LLM job (c).

Readonly score/safety fields are overwritten from the scorer; any ID outside the allowlists, or
pass-style wording after a failed Critical Safety gate, drops the output for the template debrief.
"""

import json
from dataclasses import dataclass

from app.ai.contracts import DebriefOutput, DebriefPoint
from app.ai.intent import V2
from app.ai.llm_client import LLMClient, LLMError

PASS_WORDING = ("ผ่าน", "สำเร็จตามเกณฑ์")


@dataclass(frozen=True)
class StepFact:
    event_id: str  # "<room_id>:<idx>"
    text_th: str  # authored feedback for the step
    dimension: str | None
    strength: bool


@dataclass(frozen=True)
class DebriefInput:
    attempt_id: str
    score_total: int | None
    safety_met: bool
    steps: tuple[StepFact, ...]
    objective_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()


def _readonly(src: DebriefInput) -> dict[str, object]:
    return {
        "attempt_id": src.attempt_id,
        "score_total_readonly": src.score_total,
        "critical_safety_result_readonly": "pass" if src.safety_met else "fail",
    }


def _point(step: StepFact, src: DebriefInput) -> DebriefPoint:
    return DebriefPoint(
        text=step.text_th,
        event_ids=[step.event_id],
        rubric_dimension_id=step.dimension,
        objective_ids=list(src.objective_ids),
    )


def template(src: DebriefInput) -> DebriefOutput:
    return DebriefOutput.model_validate(
        {
            **_readonly(src),
            "strengths": [_point(s, src) for s in src.steps if s.strength],
            "improvements": [_point(s, src) for s in src.steps if not s.strength],
            "recommended_asset_ids": list(src.asset_ids),
            "cited_claim_ids": [],
            "fallback_used": True,
        }
    )


def build_prompt(src: DebriefInput) -> str:
    return json.dumps(
        {
            "attempt_id": src.attempt_id,
            "critical_safety_result": "pass" if src.safety_met else "fail",
            "steps": [
                {
                    "event_id": s.event_id,
                    "feedback_th": s.text_th,
                    "dimension": s.dimension,
                    "safe": s.strength,
                }
                for s in src.steps
            ],
            "allowed": {
                "event_ids": [s.event_id for s in src.steps],
                "objective_ids": list(src.objective_ids),
                "claim_ids": list(src.claim_ids),
                "asset_ids": list(src.asset_ids),
            },
        },
        ensure_ascii=False,
    )


def valid(out: DebriefOutput, src: DebriefInput) -> bool:
    events = {s.event_id for s in src.steps}
    points = [*out.strengths, *out.improvements]
    if out.attempt_id != src.attempt_id or not points:
        return False
    for p in points:
        if not set(p.event_ids) <= events or not set(p.objective_ids) <= set(src.objective_ids):
            return False
        if p.rubric_dimension_id not in (None, *src.dimensions):
            return False
        if not src.safety_met and any(w in p.text for w in PASS_WORDING):
            return False
    return set(out.recommended_asset_ids) <= set(src.asset_ids) and set(out.cited_claim_ids) <= set(
        src.claim_ids
    )


def debrief(client: LLMClient, src: DebriefInput) -> tuple[DebriefOutput, str | None]:
    """(output, fallback_reason). The reason is None when the model output was accepted."""
    try:
        raw = client.complete_structured(
            DebriefOutput,
            purpose="debrief",
            system=(V2 / "debrief.md").read_text(encoding="utf-8"),
            prompt=build_prompt(src),
            temperature=0.3,
            max_tokens=1200,
        )
    except LLMError as exc:
        return template(src), f"llm_{type(exc).__name__.lower()}"
    if not valid(raw, src):
        return template(src), "validator:membership"
    return raw.model_copy(update={**_readonly(src), "fallback_used": False}), None
