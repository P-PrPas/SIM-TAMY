"""Learning examples remain reproducible and use the content/engine contracts."""

import json

import pytest
import yaml

from app.ai.llm_client import LLMClient
from app.content.loader import load_case
from scripts import build_course_replays as builder
from scripts.build_course_replays import ROOT, SOURCES, build


@pytest.mark.parametrize("source", SOURCES)
def test_checked_in_course_example_matches_its_golden_source(source):
    recording = build(source)
    path = ROOT / "recordings" / f"{recording.recording_id}.json"
    assert json.loads(path.read_text("utf-8")) == recording.model_dump(
        mode="json", exclude_none=True
    )
    assert recording.case_id != "DEV-001"
    assert recording.case.status == "Draft"
    assert recording.steps[0].speaker == "learner"
    assert recording.steps[-1].type == "complete"
    replies = [step.text for step in recording.steps if step.speaker == "patient"]
    assert len(replies) == len(set(replies)), "do not repeat canned context for unrelated questions"


def test_all_examples_build_without_an_llm(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("authored examples must not call an LLM")

    monkeypatch.setattr(LLMClient, "_run", forbidden)
    for source in SOURCES:
        build(source)


@pytest.mark.parametrize("invalid", ["leak", "fact", "action", "version", "missing_turn"])
def test_invalid_authored_dialogue_is_not_published(tmp_path, monkeypatch, invalid):
    dialogues = yaml.safe_load(builder.DIALOGUE_FILE.read_text("utf-8"))
    dialogue = dialogues["DAD-001"]
    if invalid == "leak":
        case = load_case(ROOT / "content/cases/DAD-001").case
        dialogue["turns"][0]["patient_th"] = next(f.text_th for f in case.facts if f.id == "H1")
    elif invalid == "fact":
        dialogue["turns"][0]["fact_ids"] = ["H1"]
    elif invalid == "action":
        dialogue["turns"][0]["learner_th"] = "unrelated question"
    elif invalid == "version":
        dialogue["case_version"] = "obsolete"
    else:
        dialogue["turns"].pop()
    file = tmp_path / "dialogue.yaml"
    file.write_text(yaml.safe_dump(dialogues, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(builder, "DIALOGUE_FILE", file)
    with pytest.raises(ValueError):
        build(SOURCES[0])


def test_measurement_is_a_source_fact_not_patient_dialogue():
    recording = build("parents/T41.yaml")
    observations = [step for step in recording.steps if step.speaker == "system"]
    case = load_case(ROOT / "content/cases/STF-002").case
    expected = next(f.text_th for f in case.facts if f.id == "H5")
    assert [step.text for step in observations] == [expected]
    assert expected not in [step.text for step in recording.steps if step.speaker == "patient"]
