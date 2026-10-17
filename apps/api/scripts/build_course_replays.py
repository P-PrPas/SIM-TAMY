"""Build synthetic examples from content-owned golden conversations; no DB or LLM."""

import json

from app.ai.lexical import match_actions
from app.ai.validator import PatientValidator
from app.api.v1.schemas import Recording, RecordingStep
from app.content.loader import load_case
from app.domain.state import AllowedFacts
from app.engine.scenario import apply
from app.golden import load_golden
from app.services.patient_voice import CannedGenerator, Voice, VoiceRequest, speak
from scripts.build_dev_replay import ROOT, assemble
from tests.unit.engine.play import Play

SOURCES = [
    "parents/T21.yaml",
    "parents/T26.yaml",
    "parents/T31.yaml",
    "parents/T36.yaml",
    "parents/T41.yaml",
    "pp001/T11.yaml",
]


def build(source: str) -> Recording:
    golden = load_golden(ROOT / "eval/golden" / source)
    loaded = load_case(ROOT / "content/cases" / golden.case)
    play = Play(loaded, golden.variant)
    steps: list[RecordingStep] = []
    for step in golden.steps:
        if step.say is not None:
            actions = [action.id for action in match_actions(step.say, loaded.actions)]
            allowed: AllowedFacts = apply(play.state, actions, loaded.case, golden.variant).allowed
            play.turn(*actions)
            request = VoiceRequest(
                loaded.case.variants[golden.variant].persona.style_th,
                allowed,
                "answer",
                step.say,
                learner_audience=loaded.case.audience,
            )
            spoken = speak(
                request,
                loaded.case,
                play.state.revealed_fact_ids,
                Voice(CannedGenerator(), PatientValidator(request)),
            )
            assert spoken.text
            steps.extend(
                [
                    RecordingStep(t_ms=800, type="learner", speaker="learner", text=step.say),
                    RecordingStep(t_ms=1200, type="reply", speaker="patient", text=spoken.text),
                ]
            )
        elif step.decision is not None:
            play.decide(step.decision)
            steps.append(RecordingStep(t_ms=800, type="decision", option_id=step.decision))
        elif step.complete:
            if step.note:
                play.note(len(step.note.strip()))
            play.complete()
            steps.append(RecordingStep(t_ms=800, type="complete"))
    recording = assemble(loaded, play, steps, f"{golden.case.lower()}-example")
    assert recording.report.effective.safety_status == golden.expect.safety_status
    return recording


def main() -> None:
    for source in SOURCES:
        recording = build(source)
        destination = ROOT / "recordings" / f"{recording.recording_id}.json"
        destination.write_bytes(
            (
                json.dumps(
                    recording.model_dump(mode="json", exclude_none=True),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8"),
        )
        print(destination)


if __name__ == "__main__":
    main()
