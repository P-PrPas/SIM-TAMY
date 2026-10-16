"""Build an offline engineering-only recording from DEV-001 and the real scoring engine.

Run from apps/api: python -m scripts.build_dev_replay. Never use as clinical demo content.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.api.v1.schemas import Recording, RecordingStep
from app.content.loader import load_case
from app.engine.findings import build_findings
from app.engine.glassbox import build_glassbox
from app.engine.replay import build_replay
from app.engine.scoring import score
from app.services.briefs import case_brief, disclaimer_th, replay_notes
from app.services.closing import _assemble, _template_debrief
from tests.unit.engine.play import Play

ROOT = Path(__file__).resolve().parents[3]
LOADED = load_case(ROOT / "content" / "cases" / "DEV-001")
RECORDING_ID = "dev001-engineering"


def build() -> Recording:
    play = Play(LOADED, "A")
    steps: list[RecordingStep] = []
    actions = {action.id: action for action in LOADED.actions}
    facts = {fact.id: fact for fact in LOADED.case.facts}
    for ids in (("A01", "A02"), ("A03", "A04"), ("C01", "C02")):
        start = len(play.events)
        steps.append(
            RecordingStep(
                t_ms=350,
                type="learner",
                speaker="learner",
                text=" ".join(actions[id_].examples_th[0] for id_ in ids),
            )
        )
        play.turn(*ids)
        revealed = [e.payload["id"] for e in play.events[start:] if e.type == "FACT_REVEALED"]
        reply = " ".join(facts[id_].text_th for id_ in revealed)
        if not reply:
            reply = LOADED.case.patient_profile.display_th
        steps.append(RecordingStep(t_ms=500, type="reply", speaker="patient", text=reply))

    play.decide("refer").note(30).complete()
    steps.append(RecordingStep(t_ms=450, type="decision", option_id="refer"))
    steps.append(RecordingStep(t_ms=350, type="complete"))
    scoring = score(play.events, LOADED.rubric, LOADED.actions, "A")
    findings = build_findings(scoring.items, LOADED.rubric)
    saved = SimpleNamespace(
        created_at=datetime(2026, 10, 16, tzinfo=UTC),
        rubric_version=LOADED.rubric.rubric_version,
        debrief=_template_debrief(findings).model_dump(mode="json"),
        glassbox=build_glassbox(play.events, LOADED.case, LOADED.actions).model_dump(mode="json"),
        replay=build_replay(play.events, LOADED.case, disclaimer_th(), replay_notes()).model_dump(
            mode="json"
        ),
    )
    row = SimpleNamespace(id=uuid.UUID("00000000-0000-0000-0000-000000000073"), variant="A")
    report = _assemble(row, LOADED, saved, scoring, findings, play.events)
    return Recording(
        recording_id=RECORDING_ID,
        title_th=LOADED.case.title_th,
        description_th=disclaimer_th(),
        case_id=LOADED.case.case_id,
        variant="A",
        steps_count=len(steps),
        case=case_brief(LOADED),
        steps=steps,
        report=report,
    )


if __name__ == "__main__":
    destination = ROOT / "recordings" / f"{RECORDING_ID}.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(
        json.dumps(
            build().model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    print(destination)
