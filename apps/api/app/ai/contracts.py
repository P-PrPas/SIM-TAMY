"""Versioned AI I/O schemas for SIM-TAMY 2.0 (Blueprint §09B-09D, ADR-15).

Model output is parsed into these models, then checked against server-side allowlists; anything
outside an allowlist is dropped or the call falls back. Learner and claim text are data.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# AI-01: generic intents every family step accepts, beside its own intent/choice IDs.
GENERIC_INTENTS: frozenset[str] = frozenset(
    {"REQUEST_CLARIFICATION", "DISCUSS_WITH_PARTNER", "OUT_OF_SCOPE", "REAL_WORLD_HEALTH_QUERY"}
)
ACCEPT_BELOW = 0.25  # uncertainty <= 0.25 ~ confidence >= 0.75 (AGENTS confidence policy)
CLARIFY_BELOW = 0.5  # 0.25-0.5 clarify; above: ignore, no state change


class _Out(BaseModel):
    # Lenient on extra keys from the model (AI-T04): they are ignored, never acted on.
    model_config = ConfigDict(extra="ignore", frozen=True)


class ContextReference(_Out):
    topic_id: str | None = None  # an intent/fact ID mentioned earlier by this role
    turn_ref: int | None = None  # message index of this role's earlier turn


class IntentInterpretation(_Out):
    """ai.intent.v1: what the learner meant. Never a committed decision or a state change."""

    schema_version: Literal["ai.intent.v1"] = "ai.intent.v1"
    intent_code: str  # a step intent ID, a step choice ID, or one of GENERIC_INTENTS
    requested_fact_ids: list[str] = []
    context_reference: ContextReference | None = None
    needs_clarification: bool = False
    uncertainty_score: float = Field(default=1.0, ge=0, le=1)  # uncalibrated routing hint


class CitedClaim(_Out):
    knowledge_id: str
    knowledge_version: str
    claim_id: str
    source_id: str
    source_locator: str


class EvidenceItem(_Out):
    """One claim the controller allows in a reply; built from a pinned KnowledgeRelease."""

    knowledge_id: str
    knowledge_version: str
    claim_id: str
    source_id: str
    source_locator: str
    allowed_text_th: str


class EvidencePack(_Out):
    release_id: str
    allowed_fact_ids: list[str] = []  # scenario facts this role may hear now
    items: list[EvidenceItem] = []

    def cites(self, claim: CitedClaim) -> bool:
        return any(
            (i.knowledge_id, i.knowledge_version, i.claim_id, i.source_id, i.source_locator)
            == (
                claim.knowledge_id,
                claim.knowledge_version,
                claim.claim_id,
                claim.source_id,
                claim.source_locator,
            )
            for i in self.items
        )


SafetyRoute = Literal["normal", "boundary", "high_risk_template"]


class GroundedReply(_Out):
    """ai.grounded_reply.v1: a character/explainer reply composed only from the pack."""

    schema_version: Literal["ai.grounded_reply.v1"] = "ai.grounded_reply.v1"
    reply_text: str
    used_scenario_fact_ids: list[str] = []
    cited_claims: list[CitedClaim] = []
    knowledge_release_snapshot_id: str
    safety_route: SafetyRoute = "normal"
    fallback_used: bool = False


class DebriefPoint(_Out):
    text: str
    event_ids: list[str] = Field(min_length=1)  # family event IDs: "<room_id>:<idx>"
    rubric_dimension_id: str | None = None
    objective_ids: list[str] = []


class DebriefOutput(_Out):
    """ai.debrief.v1. Readonly fields are overwritten from the scorer before anything is shown."""

    schema_version: Literal["ai.debrief.v1"] = "ai.debrief.v1"
    attempt_id: str
    score_total_readonly: int | None = None
    critical_safety_result_readonly: Literal["pass", "fail"] | None = None
    strengths: list[DebriefPoint] = []
    improvements: list[DebriefPoint] = []
    recommended_asset_ids: list[str] = []
    cited_claim_ids: list[str] = []
    fallback_used: bool = False
