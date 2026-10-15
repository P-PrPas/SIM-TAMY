"""What a learner may see of a case before and during play (openapi `CaseBrief`, `Notice`).

No hidden facts, rubric, branch rules or outcome scripts come through here (AGENTS.md rule 5).
Reused by the read endpoints (T-045).
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.api.v1.schemas import (
    CaseBrief,
    CaseStatus,
    DecisionOption,
    LearningObjective,
    Limits,
    Notice,
    Variant,
)
from app.content.loader import LoadedCase
from app.core import limits

# ponytail: Variant C needs the pressure scene (T-023); hidden until it exists.
PLAYABLE_VARIANTS: tuple[str, ...] = ("A", "B")

LIMITS = Limits(
    max_turns=limits.MAX_TURNS,
    max_text_chars=limits.MAX_TEXT_CHARS,
    idle_timeout_s=limits.IDLE_TIMEOUT_S,
    max_rationale_chars=limits.MAX_RATIONALE_CHARS,
    max_note_chars=limits.MAX_NOTE_CHARS,
)


@lru_cache
def _ui() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "ai" / "prompts" / "notices_th.yaml"
    loaded = yaml.safe_load(path.read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def status_label(status: str) -> str:
    return str(_ui()["status_labels"][status])


def disclaimer_th() -> str:
    return str(_ui()["disclaimer_th"])


def playable_variants(loaded: LoadedCase) -> list[Variant]:
    return [Variant(v) for v in loaded.case.variants if v in PLAYABLE_VARIANTS]


def case_brief(loaded: LoadedCase) -> CaseBrief:
    c = loaded.case
    return CaseBrief(
        case_id=c.case_id,
        version=c.version,
        title_th=c.title_th,
        status=CaseStatus(c.status),
        status_label_th=status_label(c.status),
        variants_available=playable_variants(loaded),
        patient_display_th=c.patient_profile.display_th,
        # ponytail: the Case schema stores objective ids only; the id doubles as the label
        learning_objectives=[LearningObjective(id=o, label_th=o) for o in c.learning_objectives],
        decision_options=[DecisionOption(id=o.id, label_th=o.label_th) for o in c.decision_options],
        disclaimer_th=disclaimer_th(),
    )


def notices(loaded: LoadedCase) -> list[Notice]:
    text = _ui()["notices"]
    return [
        Notice(code="EDUCATION_ONLY", text_th=text["EDUCATION_ONLY"]),
        Notice(code="CASE_STATUS", text_th=status_label(loaded.case.status)),
        Notice(code="PRIVACY_LLM", text_th=text["PRIVACY_LLM"]),
        Notice(code="NO_REAL_PII", text_th=text["NO_REAL_PII"]),
    ]
