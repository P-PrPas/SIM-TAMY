"""Offline, deterministic answers for the v2 prompts (AI-01/02/03), so CI never needs a network.

Selected by the `prompt_version:` first line of the system prompt. Scripted rules in the mock
provider's YAML still win; these are the defaults. A pure function of the prompt: no randomness.
"""

import json
from typing import Any

from app.ai.thai import normalize_th

ANAPHORA = ("เรื่องนั้น", "ข้อนี้", "อันนั้น", "แล้วล่ะ", "ต่อจากนั้น", "เรื่องเมื่อกี้", "อีกที")
CLARIFY = ("ไม่เข้าใจ", "หมายความว่า", "อธิบายอีกที", "พูดอีกที", "ขยายความ")
PARTNER = (
    "ปรึกษาสามี",
    "ปรึกษาภรรยา",
    "ปรึกษาแฟน",
    "คุยกับสามี",
    "คุยกับภรรยา",
    "คุยกับคู่",
    "ถามนนท์",
    "ถามมะลิ",
)
ACCEPT_OVERLAP = 0.8
CLARIFY_OVERLAP = 0.55
MIN_CHARS = 6


def _bigrams(text: str) -> set[str]:
    flat = normalize_th(text).replace(" ", "").casefold()
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


def _overlap(text: str, phrase: str) -> float:
    a, b = _bigrams(text), _bigrams(phrase)
    if not a or not b:
        return 0.0
    return max(len(a & b) / len(a), len(a & b) / len(b))


def _score(text: str, option: dict[str, Any]) -> float:
    flat = normalize_th(text).casefold()
    best = 0.0
    for phrase in [option["label"], *option.get("examples", [])]:
        needle = normalize_th(phrase).casefold()
        if needle in flat or (len(flat) >= MIN_CHARS and flat in needle):
            return 1.0
        best = max(best, _overlap(text, phrase))
    return best


def intent(payload: dict[str, Any]) -> dict[str, Any]:
    text = normalize_th(payload["learner_text"]).casefold()
    allowed = payload["allowed"]
    if any(m in text for m in CLARIFY):
        return {"intent_code": "REQUEST_CLARIFICATION", "uncertainty_score": 0.1}
    if any(m in text for m in PARTNER):
        return {"intent_code": "DISCUSS_WITH_PARTNER", "uncertainty_score": 0.1}
    scored = sorted(((_score(text, o), o["id"]) for o in allowed), key=lambda s: (-s[0], s[1]))
    best, code = scored[0] if scored else (0.0, "OUT_OF_SCOPE")
    if best >= ACCEPT_OVERLAP:
        return {"intent_code": code, "uncertainty_score": 0.1}
    previous = next((h for h in reversed(payload["history"]) if h.get("intent_code")), None)
    if previous and any(m in text for m in ANAPHORA) and best < CLARIFY_OVERLAP:
        return {
            "intent_code": previous["intent_code"],
            "context_reference": {"topic_id": previous["intent_code"]},
            "uncertainty_score": 0.2,
        }
    if best >= CLARIFY_OVERLAP:
        return {"intent_code": code, "uncertainty_score": 0.4, "needs_clarification": True}
    return {"intent_code": "OUT_OF_SCOPE", "uncertainty_score": 0.1}


_SNIPPET = 280


def grounded_reply(payload: dict[str, Any]) -> dict[str, Any]:
    facts = {f["id"]: f["text"] for f in payload["allowed_facts"]}
    wanted = payload["must_use_fact_ids"] or list(facts)[:1]
    items = payload["evidence"]["items"]
    text = " ".join(facts[i] for i in wanted if i in facts)
    cited: list[dict[str, str]] = []
    if items and not text:
        item = items[0]
        text = item["allowed_text_th"]
        cited = [
            {k: item[k] for k in ("knowledge_id", "knowledge_version", "claim_id", "source_id")}
            | {"source_locator": item["source_locator"]}
        ]
    return {
        "reply_text": text[:_SNIPPET],
        "used_scenario_fact_ids": [i for i in wanted if i in facts],
        "cited_claims": cited,
        "knowledge_release_snapshot_id": payload["evidence"]["release_id"],
    }


def debrief(payload: dict[str, Any]) -> dict[str, Any]:
    def point(step: dict[str, Any]) -> dict[str, Any]:
        return {
            "text": step["feedback_th"],
            "event_ids": [step["event_id"]],
            "rubric_dimension_id": step["dimension"],
            "objective_ids": payload["allowed"]["objective_ids"],
        }

    steps = payload["steps"]
    return {
        "attempt_id": payload["attempt_id"],
        "strengths": [point(s) for s in steps if s["safe"]],
        "improvements": [point(s) for s in steps if not s["safe"]],
        "recommended_asset_ids": payload["allowed"]["asset_ids"],
        "cited_claim_ids": [],
    }


def respond(system: str, prompt: str) -> str | None:
    """JSON text for a v2 prompt, or None when `system` is not a v2 prompt."""
    version = system.lstrip().splitlines()[0] if system.strip() else ""
    if not version.startswith("prompt_version: ai."):
        return None
    payload = json.loads(prompt)
    kind = version.split(".")[1]
    handler = {"intent": intent, "grounded_reply": grounded_reply, "debrief": debrief}[kind]
    return json.dumps(handler(payload), ensure_ascii=False, sort_keys=True)
