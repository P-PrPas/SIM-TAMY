"""Generator-only grandmother phrasing, gated by exact content-authored alternatives."""

import json
from pathlib import Path

from app.ai.llm_client import LLMClient, LLMError

SYSTEM = Path(__file__).resolve().parent / "prompts" / "family_generator.md"


def reply(client: LLMClient, *, persona: str, learner_text: str, allowed: list[str]) -> str:
    if not allowed:
        raise ValueError("at least one authored fallback is required")
    prompt = json.dumps(
        {"persona": persona, "learner_text": learner_text, "allowed_replies": allowed},
        ensure_ascii=False,
    )
    for _ in range(3):  # initial generation plus at most two regenerations
        try:
            text = client.complete_text(
                purpose="generator",
                system=SYSTEM.read_text("utf-8"),
                prompt=prompt,
                temperature=0.5,
                max_tokens=300,
            ).strip()
        except LLMError:
            break
        # No rejected text is persisted, returned or streamed. Facts cannot be improvised.
        if text in allowed:
            return text
    return allowed[0]
