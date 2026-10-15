"""Fail if a play-time schema in docs/openapi.yaml can carry hidden information (API_DESIGN 6).

Walks every `$ref` below the schemas a learner receives during play and reports forbidden field
names. The one deliberate exception is `TurnResponse.glassbox` (null unless GLASS_BOX_LIVE).
"""

import sys
from pathlib import Path
from typing import Any

import yaml

SPEC = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
PLAY_TIME = [
    "SessionView",
    "TurnResponse",
    "Reply",
    "CreateSessionResponse",
    "DecisionResponse",
    "CompleteResponse",
    "Message",
    "DecisionState",
    "Notice",
    "CaseBrief",
    "CaseSummary",
]
FORBIDDEN = {
    "revealed_fact_ids",
    "fired_action_ids",
    "risk_state",
    "risk_state_timeline",
    "actions",
    "facts",
    "hidden_facts",
    "unlock_on",
    "leak_terms_th",
    "keywords_th",
    "fallback_utterances_th",
    "rubric",
    "items",
    "findings",
    "evidence",
    "total_score",
    "safety_status",
    "score_pct",
    "competencies",
    "branch_rules",
    "outcome_scripts",
}
ALLOWED_EDGES = {("TurnResponse", "glassbox")}  # LiveGlassBox: only when the flag is on


def check(spec: dict[str, Any]) -> list[str]:
    schemas = spec["components"]["schemas"]
    problems: list[str] = []

    def walk(node: Any, trail: str, root: str, seen: frozenset[str]) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, trail, root, seen)
        elif isinstance(node, dict):
            ref = node.get("$ref")
            if ref:
                name = ref.rsplit("/", 1)[-1]
                if name not in seen and name in schemas:
                    walk(schemas[name], f"{trail} -> {name}", root, seen | {name})
                return
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    for field, sub in value.items():
                        if (root, field) in ALLOWED_EDGES and trail.count("->") == 0:
                            continue
                        if field in FORBIDDEN:
                            problems.append(f"{trail}: forbidden field '{field}'")
                        walk(sub, f"{trail}.{field}", root, seen)
                else:
                    walk(value, trail, root, seen)

    for name in PLAY_TIME:
        walk(schemas[name], name, name, frozenset({name}))
    return problems


def main() -> int:
    problems = check(yaml.safe_load(SPEC.read_text(encoding="utf-8")))
    for p in problems:
        print(p)
    print("leakcheck:", "FAILED" if problems else "clean", f"({len(PLAY_TIME)} schemas)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
