"""Course relationships survive prompt generation and the hard reply gate."""

from pathlib import Path

import pytest
import yaml

from app.ai.validator import PatientValidator
from app.content.loader import load_case
from app.domain.state import AllowedFacts
from app.services.patient_voice import VoiceRequest

ROOT = Path(__file__).resolve().parents[5]


@pytest.mark.parametrize(
    ("case_id", "relationship"),
    [
        ("DAD-001", "สามี"),
        ("DAD-002", "สามี"),
        ("MOM-001", "เพื่อน"),
        ("MOM-002", "เพื่อน"),
        ("PP-001", "เจ้าหน้าที่"),
        ("STF-002", "เจ้าหน้าที่"),
    ],
)
@pytest.mark.parametrize("variant", ["A", "C"])
def test_every_course_persona_names_the_learners_relationship(case_id, relationship, variant):
    case = load_case(ROOT / "content" / "cases" / case_id).case
    assert relationship in case.variants[variant].persona.style_th


@pytest.mark.parametrize("audience", ["dad", "mom", "staff"])
def test_patient_does_not_assign_an_unverified_medical_title(audience):
    request = VoiceRequest(
        persona_style_th="style",
        allowed=AllowedFacts(),
        directive="deflect_smalltalk",
        learner_text="question",
        learner_audience=audience,
    )
    rules = (ROOT / "apps/api/app/ai/prompts/validator_rules.yaml").read_text("utf-8")
    case = load_case(ROOT / "content/cases/DEV-001").case
    for title in yaml.safe_load(rules)["unverified_medical_titles"]:
        assert PatientValidator(request).check(title, case, []) == ["learner_role"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ปวดท้องค่ะ คุณหมอ", ["learner_role"]),
        ("ปวดมากเลย คุณหมอ", ["learner_role"]),
        ("ปวดหลัง หมอคะ", ["learner_role"]),
        ("ไม่แน่ใจเหมือนกัน พี่หมอ ช่วยดูหน่อย", ["learner_role"]),
        ("เมื่อวานไปหาคุณหมอมา", []),
        ("เมื่อวานไปหา คุณหมอมา", []),
    ],
)
def test_whitespace_vocatives_preserve_third_person_mentions(text, expected):
    request = VoiceRequest(
        persona_style_th="style",
        allowed=AllowedFacts(),
        directive="deflect_smalltalk",
        learner_text="question",
        learner_audience="dad",
    )
    case = load_case(ROOT / "content/cases/DEV-001").case
    assert PatientValidator(request).check(text, case, []) == expected
