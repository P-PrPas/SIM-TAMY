"""Hard patient reply gate (PRD 9.3, T-034). First failed rule wins."""

import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import yaml

from app.ai.thai import normalize_th
from app.domain.case import Case, HiddenFact
from app.services.patient_voice import MAX_CHARS, VoiceRequest

_RULES = Path(__file__).resolve().parent / "prompts" / "validator_rules.yaml"
_SENTENCE = re.compile(r"[.!?。！？\n]+")
_NUMBER = re.compile(r"(?<![0-9๐-๙])(?:[0-9๐-๙]+(?:[.,][0-9๐-๙]+)?)(?:\s*[A-Za-zก-๙%]+)?")


@lru_cache
def _role_break_phrases() -> tuple[str, ...]:
    loaded = yaml.safe_load(_RULES.read_text(encoding="utf-8"))
    return tuple(normalize_th(s).casefold() for s in loaded["role_break_phrases"])


@lru_cache
def _unverified_medical_titles() -> tuple[str, ...]:
    loaded = yaml.safe_load(_RULES.read_text(encoding="utf-8"))
    return tuple(normalize_th(s).casefold() for s in loaded["unverified_medical_titles"])


@lru_cache
def _learner_address_pattern() -> re.Pattern[str]:
    loaded = yaml.safe_load(_RULES.read_text(encoding="utf-8"))
    titles = "|".join(re.escape(title) for title in _unverified_medical_titles())
    return re.compile(str(loaded["learner_address_boundary"]) + f"(?:{titles})")


class PatientValidator:
    def __init__(self, request: VoiceRequest) -> None:
        self.request = request

    def check(self, text: str, case: Case, revealed: Sequence[str]) -> list[str]:
        flat = normalize_th(text)
        folded = flat.casefold()
        if len(flat) > MAX_CHARS or len([s for s in _SENTENCE.split(text) if s.strip()]) > 3:
            return ["length"]
        if any(normalize_th(term).casefold() in folded for term in case.forbidden_terms_th):
            return ["forbidden_term"]
        for fact in case.facts:
            if not isinstance(fact, HiddenFact) or fact.id in revealed:
                continue
            if any(normalize_th(term).casefold() in folded for term in fact.leak_terms_th):
                return [f"leak_term:{fact.id}"]

        allowed_text = " ".join(f.text_th for f in self.request.allowed.facts)
        allowed_numbers = {
            normalize_th(match.group()).casefold() for match in _NUMBER.finditer(allowed_text)
        }
        if any(
            normalize_th(match.group()).casefold() not in allowed_numbers
            for match in _NUMBER.finditer(flat)
        ):
            return ["unsupported_number"]
        if any(phrase in folded for phrase in _role_break_phrases()):
            return ["role_break"]
        if self.request.learner_audience and _learner_address_pattern().search(folded):
            return ["learner_role"]
        if self.request.directive == "answer":
            by_id = {f.id: f for f in case.facts if isinstance(f, HiddenFact)}
            for fact_id in self.request.allowed.must_convey_fact_ids:
                required = by_id.get(fact_id)
                if required and not any(
                    normalize_th(keyword).casefold() in folded for keyword in required.keywords_th
                ):
                    return [f"must_convey:{fact_id}"]
        return []
