"""S2-01: the mock institution file is valid, labeled demo, and rejects broken references."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.institution import Institutions, load_institutions

CONTENT = Path(__file__).resolve().parents[5] / "content"


def test_shipped_file_has_two_orgs_with_staff_and_paired_learners() -> None:
    data = load_institutions(CONTENT)
    assert data.demo is True and len(data.orgs) == 2
    for org in data.orgs:
        roles = sorted(a.role for a in data.accounts if a.org_id == org.id and a.role != "learner")
        assert roles == ["educator", "educator", "org_admin", "reviewer"]
    learners = [a for a in data.accounts if a.role == "learner"]
    assert len(learners) >= 6 and any(a.partner_id for a in learners)
    assert all("สาธิต" in a.display_name_th for a in data.accounts)  # labeled demo


def _raw() -> dict:
    return load_institutions(CONTENT).model_dump()


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d["accounts"].append(dict(d["accounts"][0])),  # duplicate id
        lambda d: d["accounts"][0].update(org_id="org-missing"),
        lambda d: d["accounts"][0].update(org_id=None),  # staff without an org
        lambda d: d["accounts"][-1].update(partner_id="staff-h-admin"),  # not reciprocal
        lambda d: d.update(demo=False),
    ],
)
def test_broken_references_are_rejected(edit) -> None:
    data = _raw()
    edit(data)
    with pytest.raises(ValidationError):
        Institutions.model_validate(data)
