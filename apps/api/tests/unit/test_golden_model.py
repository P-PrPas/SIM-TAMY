"""The golden file model and expectation checks (no database)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.golden import Expect, Facts, Golden, check, load_golden

GOLDEN_DIR = Path(__file__).resolve().parents[4] / "eval" / "golden"


def facts(**kw: object) -> Facts:
    base = dict(
        safety_status="SAFETY_MET", event_types={"A"}, items={"R1": "pass"}, revealed={"H1"},
        terminal_state="Referral", missed=set(), step_rate=1.0,
    )  # fmt: skip
    return Facts(**{**base, **kw})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("expect", "overrides", "failures"),
    [
        (Expect(safety_status="SAFETY_MET"), {}, 0),
        (Expect(safety_status="SAFETY_NOT_MET"), {}, 1),
        (Expect(events_include=["A", "B"]), {}, 1),
        (Expect(events_exclude=["A"]), {}, 1),
        (Expect(items={"R1": "fail"}), {}, 1),
        (Expect(revealed=["H1"]), {}, 0),
        (Expect(revealed=[]), {}, 1),
        (Expect(replay_terminal_state="UnsafeProceed"), {}, 1),
        (Expect(replay_missed_opportunities_include=["H1"]), {}, 1),
        (Expect(replay_missed_opportunities_include=["H1"]), {"missed": {"H1"}}, 0),
        (Expect(min_step_pass_rate=0.9), {"step_rate": 0.8}, 1),
        (Expect(min_step_pass_rate=0.9), {"step_rate": None}, 1),
    ],
)
def test_check_reports_every_expectation_that_does_not_hold(
    expect: Expect, overrides: dict[str, object], failures: int
) -> None:
    assert len(check(expect, facts(**overrides))) == failures


def test_a_step_is_exactly_one_kind() -> None:
    base = {"id": "X", "expect": {}}
    with pytest.raises(ValidationError):
        Golden.model_validate({**base, "steps": [{"say": "a", "decision": "refer"}]})
    with pytest.raises(ValidationError):
        Golden.model_validate({**base, "steps": [{"note": "nothing to do"}]})


def test_unknown_keys_are_rejected_so_a_typo_cannot_silently_skip_a_check() -> None:
    with pytest.raises(ValidationError):
        Golden.model_validate({"id": "X", "steps": [{"say": "a"}], "expect": {"safety_staus": "x"}})


def test_every_shipped_golden_file_parses_and_ids_match_file_names() -> None:
    files = sorted(GOLDEN_DIR.glob("T*.yaml"))
    assert [f.stem for f in files] == [f"T{n:02d}" for n in range(1, 11)]
    assert all(load_golden(f).id == f.stem for f in files)
