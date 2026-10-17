"""Every shipped lesson exposes readable objectives without changing their IDs."""

from pathlib import Path

import pytest

from app.content.loader import load_case
from app.services.briefs import case_brief

CASES = Path(__file__).resolve().parents[4] / "content" / "cases"


@pytest.mark.parametrize("case_dir", sorted(CASES.iterdir()), ids=lambda path: path.name)
def test_all_lessons_have_thai_learning_objective_labels(case_dir):
    loaded = load_case(case_dir)
    objectives = case_brief(loaded).learning_objectives

    assert [objective.id for objective in objectives] == loaded.case.learning_objectives
    for objective in objectives:
        assert objective.label_th != objective.id
        assert "_" not in objective.label_th
        assert any("\u0e00" <= char <= "\u0e7f" for char in objective.label_th)
