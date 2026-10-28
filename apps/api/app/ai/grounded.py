"""AI-02 (contracts section 5): a character reply composed only from allowed facts + evidence.

Generator -> Validator -> up to 2 regenerations -> authored fallback (citations hidden). The
validator is hard: a rejected reply is never returned. LLM job (b) only; it never decides a reveal.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, NamedTuple

from app.ai.contracts import CitedClaim, EvidencePack, GroundedReply
from app.ai.intent import V2, _rules
from app.ai.llm_client import LLMClient, LLMError
from app.ai.thai import normalize_th
from app.ai.validator import _role_break_phrases
from app.services.patient_voice import MAX_CHARS

MAX_REGENERATIONS = 2
_SENTENCE = re.compile(r"[.!?。！？\n]+")
_NUMBER = re.compile(r"(?<![0-9๐-๙])(?:[0-9๐-๙]+(?:[.,][0-9๐-๙]+)?)(?:\s*[A-Za-zก-๙%]+)?")


class AllowedFact(NamedTuple):
    id: str
    text_th: str


@dataclass(frozen=True)
class GroundedRequest:
    character_th: str
    learner_text: str
    facts: tuple[AllowedFact, ...]  # scenario facts this role may hear now
    pack: EvidencePack
    must_use: tuple[str, ...] = ()  # fact IDs the reply has to convey
    need_citation: bool = False  # a knowledge answer must cite the pack
    blocked_terms: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (fact_id, leak terms) not allowed


@dataclass(frozen=True)
class GroundedResult:
    text_th: str
    citations: tuple[CitedClaim, ...]
    used_fact_ids: tuple[str, ...]
    safety_route: Literal["normal", "boundary", "high_risk_template"]
    fallback_used: bool
    status: str  # trace: valid | rejected
    fallback_reason: str | None = None
    rules: tuple[str, ...] = field(default=())


def _sentences(text: str) -> int:
    return len([s for s in _SENTENCE.split(text) if s.strip()])


def validate(reply: GroundedReply, req: GroundedRequest) -> list[str]:
    """First failed rule wins; an empty list means the reply may be shown."""
    flat = normalize_th(reply.reply_text)
    folded = flat.casefold()
    if not flat or len(flat) > MAX_CHARS or _sentences(reply.reply_text) > 3:
        return ["length"]
    allowed_ids = {f.id for f in req.facts}
    if not set(reply.used_scenario_fact_ids) <= allowed_ids:
        return ["fact_not_allowed"]
    for fact_id, terms in req.blocked_terms:
        if fact_id not in allowed_ids and any(normalize_th(t).casefold() in folded for t in terms):
            return [f"leak_term:{fact_id}"]
    if reply.knowledge_release_snapshot_id != req.pack.release_id:
        return ["release_mismatch"]
    if any(not req.pack.cites(c) for c in reply.cited_claims):
        return ["citation_not_in_pack"]
    if req.need_citation and not reply.cited_claims:
        return ["citation_required"]
    support = " ".join([f.text_th for f in req.facts] + [i.allowed_text_th for i in req.pack.items])
    allowed_numbers = {normalize_th(m.group()).casefold() for m in _NUMBER.finditer(support)}
    if any(
        normalize_th(m.group()).casefold() not in allowed_numbers for m in _NUMBER.finditer(flat)
    ):
        return ["unsupported_number"]
    if any(p in folded for p in _role_break_phrases()) or any(
        p in folded for p in _rules()["unsafe_reply"]
    ):
        return [
            "role_break" if any(p in folded for p in _role_break_phrases()) else "unsafe_advice"
        ]
    if not set(req.must_use) <= set(reply.used_scenario_fact_ids):
        return ["must_use"]
    return []


def build_prompt(req: GroundedRequest, retry_rules: Sequence[str]) -> str:
    return json.dumps(
        {
            "character": req.character_th,
            "allowed_facts": [{"id": f.id, "text": f.text_th} for f in req.facts],
            "must_use_fact_ids": list(req.must_use),
            "evidence": {
                "release_id": req.pack.release_id,
                "items": [i.model_dump() for i in req.pack.items],
            },
            "learner_text": req.learner_text,
            "retry_rules": list(retry_rules),
        },
        ensure_ascii=False,
    )


def generate(client: LLMClient, req: GroundedRequest, fallback_th: str) -> GroundedResult:
    system = (V2 / "grounded_reply.md").read_text(encoding="utf-8")
    seen: list[str] = []
    for attempt in range(1 + MAX_REGENERATIONS):
        try:
            reply = client.complete_structured(
                GroundedReply,
                purpose="generator",
                system=system,
                prompt=build_prompt(req, seen if attempt else ()),
                temperature=0.4,
                max_tokens=400,
            )
        except LLMError:
            seen = ["llm_error"]
            break
        failed = validate(reply, req)
        if not failed:
            return GroundedResult(
                reply.reply_text.strip(),
                tuple(reply.cited_claims),
                tuple(reply.used_scenario_fact_ids),
                "normal",
                False,
                "valid",
            )
        seen = failed
    return GroundedResult(
        fallback_th,
        (),
        (),
        "normal",
        True,
        "rejected",
        f"validator:{seen[0]}" if seen and seen[0] != "llm_error" else "llm_error",
        tuple(seen),
    )
