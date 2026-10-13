"""DEV-001 is the engineering fixture the whole pipeline runs on until PP-001 arrives (T-011)."""

from pathlib import Path

from app.content.loader import load_case
from app.content.validate import check

DEV_001 = Path(__file__).resolve().parents[5] / "content" / "cases" / "DEV-001"
MIN_ACTIONS = {
    *(f"A0{i}" for i in range(1, 8)),
    *(f"B0{i}" for i in range(1, 4)),
    *(f"C0{i}" for i in range(1, 5)),
    "D01",
}


def test_dev001_passes_strict_validation() -> None:
    assert check(load_case(DEV_001), strict=True) == []


def test_dev001_covers_the_minimum_contract() -> None:
    loaded = load_case(DEV_001)
    case = loaded.case
    assert case.status == "Draft" and "DEV-001" in case.title_th
    assert {a.id for a in loaded.actions} >= MIN_ACTIONS
    assert set(case.variants) == {"A", "C"} and case.variants["C"].pressure_script
    assert {"Referral", "UnsafeProceed"} <= set(case.outcome_scripts)
    # all 10 rubric check types are exercised, so T-060 can build its tests on this fixture
    assert len({i.check.type for i in loaded.rubric.items}) == 10
    assert any(i.critical for i in loaded.rubric.items)
