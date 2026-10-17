"""Build authored examples with golden-equivalent actions; no DB or LLM."""

import json
import uuid
from dataclasses import replace

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.ai.lexical import match_actions
from app.ai.validator import PatientValidator
from app.api.v1.schemas import Recording, RecordingStep
from app.content.loader import load_case
from app.domain.state import AllowedFacts
from app.engine.scenario import apply
from app.golden import load_golden
from app.services.patient_voice import VoiceRequest
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
DIALOGUE_FILE = ROOT / "content/examples/dialogues_th.yaml"


class ExampleTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_th: str = Field(min_length=1, max_length=500)
    patient_th: str = Field(min_length=1, max_length=300)
    fact_ids: list[str] = Field(default_factory=list)
    observation_fact_ids: list[str] = Field(default_factory=list)


class ExampleDialogue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_version: str
    turns: list[ExampleTurn]


def build(source: str) -> Recording:
    golden = load_golden(ROOT / "eval/golden" / source)
    loaded = load_case(ROOT / "content/cases" / golden.case)
    dialogues = TypeAdapter(dict[str, ExampleDialogue]).validate_python(
        yaml.safe_load(DIALOGUE_FILE.read_text("utf-8"))
    )
    dialogue = dialogues[golden.case]
    if dialogue.case_version != loaded.case.version:
        raise ValueError("review dialogue after case version changes")
    if len(dialogue.turns) != sum(step.say is not None for step in golden.steps):
        raise ValueError("dialogue must cover every golden learner turn")
    turns = iter(dialogue.turns)
    play = Play(loaded, golden.variant)
    steps: list[RecordingStep] = []
    for step in golden.steps:
        if step.say is not None:
            turn = next(turns)
            actions = [action.id for action in match_actions(turn.learner_th, loaded.actions)]
            if actions != [action.id for action in match_actions(step.say, loaded.actions)]:
                raise ValueError(f"{golden.case}: authored question changed the golden actions")
            allowed: AllowedFacts = apply(play.state, actions, loaded.case, golden.variant).allowed
            play.turn(*actions)
            facts = {fact.id: fact for fact in allowed.facts}
            observed = set(turn.observation_fact_ids)
            declared = set(turn.fact_ids) | observed
            if not declared <= facts.keys():
                raise ValueError(f"{golden.case}: dialogue references unavailable facts")
            if not set(allowed.must_convey_fact_ids) <= declared:
                raise ValueError("new facts must be conveyed")
            if not observed <= set(allowed.must_convey_fact_ids):
                raise ValueError("observations must be newly revealed")
            request = VoiceRequest(
                loaded.case.variants[golden.variant].persona.style_th,
                allowed.model_copy(
                    update={
                        "must_convey_fact_ids": tuple(
                            fact for fact in allowed.must_convey_fact_ids if fact not in observed
                        )
                    }
                ),
                "answer",
                turn.learner_th,
                learner_audience=loaded.case.audience,
            )
            rejected = PatientValidator(request).check(
                turn.patient_th, loaded.case, play.state.revealed_fact_ids
            )
            if rejected:
                raise ValueError(f"{golden.case}: authored reply rejected: {rejected}")
            steps.extend(
                [
                    RecordingStep(
                        t_ms=800, type="learner", speaker="learner", text=turn.learner_th
                    ),
                    RecordingStep(t_ms=1200, type="reply", speaker="patient", text=turn.patient_th),
                ]
            )
            for fact_id in turn.observation_fact_ids:
                observation_request = replace(
                    request,
                    allowed=allowed.model_copy(update={"must_convey_fact_ids": (fact_id,)}),
                )
                rejected = PatientValidator(observation_request).check(
                    facts[fact_id].text_th, loaded.case, play.state.revealed_fact_ids
                )
                if rejected:
                    raise ValueError(f"{golden.case}: observation rejected: {rejected}")
                steps.append(
                    RecordingStep(
                        t_ms=800, type="reply", speaker="system", text=facts[fact_id].text_th
                    )
                )
        elif step.decision is not None:
            play.decide(step.decision)
            steps.append(RecordingStep(t_ms=800, type="decision", option_id=step.decision))
        elif step.complete:
            if step.note:
                play.note(len(step.note.strip()))
            play.complete()
            steps.append(RecordingStep(t_ms=800, type="complete"))
    recording_id = f"{golden.case.lower()}-example"
    recording = assemble(
        loaded,
        play,
        steps,
        recording_id,
        session_id=uuid.uuid5(uuid.NAMESPACE_URL, f"sim-tamy:recording:{recording_id}"),
    )
    assert recording.report.effective.safety_status == golden.expect.safety_status
    return recording


def main() -> None:
    recordings = [build(source) for source in SOURCES]
    for recording in recordings:
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
