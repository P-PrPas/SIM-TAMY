"""Learning examples remain reproducible and use the content/engine contracts."""

import json

import pytest

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
