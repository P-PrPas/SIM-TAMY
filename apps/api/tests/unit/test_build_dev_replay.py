"""The recording builder keeps working when `build_replay` changes (T-064)."""

import json

from scripts.build_dev_replay import RECORDING_ID, ROOT, build


def test_build_runs_and_its_replay_matches_the_committed_recording() -> None:
    built = build().model_dump(mode="json", exclude_none=True)
    saved = json.loads((ROOT / "recordings" / f"{RECORDING_ID}.json").read_text(encoding="utf-8"))

    assert built["steps"] == saved["steps"]
    assert built["report"]["replay"] == saved["report"]["replay"]
