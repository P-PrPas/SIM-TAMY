"""Patient wording from this turn's allowed facts only (PRD 9.2, T-033)."""

import json
from pathlib import Path

from app.ai.llm_client import LLMClient
from app.services.patient_voice import VoiceRequest

_SYSTEM = Path(__file__).resolve().parent / "prompts" / "generator.md"
_MAX_HISTORY = 4


class PatientGenerator:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def generate(self, request: VoiceRequest, attempt: int) -> str:
        # Do not serialize a Case, HiddenFact, risk state, or prior patient reply.
        # Learner history is untrusted conversational context, not a source of facts.
        history = [
            {"speaker": turn.speaker, "text": turn.text}
            for turn in request.history
            if turn.speaker == "learner"
        ][-_MAX_HISTORY:]
        prompt = json.dumps(
            {
                "persona": {
                    "style_th": request.persona_style_th,
                    "minimization": request.persona_minimization,
                    "mood": request.persona_mood,
                },
                "allowed_facts": [fact.model_dump() for fact in request.allowed.facts],
                "must_convey_fact_ids": list(request.allowed.must_convey_fact_ids),
                "directive": request.directive,
                "learner_last_text": request.learner_text,
                "history": history,
                "retry_rules": list(request.rejection_rules) if attempt else [],
            },
            ensure_ascii=False,
        )
        return self.client.complete_text(
            purpose="generator",
            system=_SYSTEM.read_text(encoding="utf-8"),
            prompt=prompt,
            temperature=0.5,
            max_tokens=150,
        )
