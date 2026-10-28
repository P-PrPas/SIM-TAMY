"""AICallTrace (Blueprint 09E): collect LLM attempts, then persist them with versions and outcome.

Only identifiers, versions and statuses are written, never prompts or replies.
"""

import uuid

from sqlalchemy.orm import Session

from app.ai.llm_client import LLMCallRecord
from app.db.repo import LlmCallRepo


class Trace:
    def __init__(self, db: Session, room_id: uuid.UUID, release_id: str | None) -> None:
        self.db, self.room_id, self.release_id = db, room_id, release_id
        self._pending: list[LLMCallRecord] = []

    def on_call(self, record: LLMCallRecord) -> None:
        self._pending.append(record)

    def close(
        self,
        capability: str,
        *,
        prompt_version: str,
        schema_version: str,
        status: str = "valid",
        fallback_reason: str | None = None,
    ) -> None:
        """Write the attempts since the last close. `status` applies to the call that succeeded."""
        for rec in self._pending:
            shown = status if rec.ok else ("timeout" if rec.error == "timeout" else "rejected")
            LlmCallRepo(self.db).record(
                purpose=rec.purpose,
                provider=rec.provider,
                model=rec.model,
                prompt_tokens=rec.prompt_tokens,
                completion_tokens=rec.completion_tokens,
                latency_ms=rec.latency_ms,
                ok=rec.ok,
                error=rec.error,
                room_id=self.room_id,
                capability=capability,
                prompt_version=prompt_version,
                schema_version=schema_version,
                validation_status=shown,
                fallback_reason=fallback_reason,
                release_id=self.release_id,
            )
        self._pending = []
