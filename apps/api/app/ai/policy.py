"""Confidence policy (PRD FR-ACT-02): what the engine may act on. Deterministic, no LLM.

>= 0.75 accept; 0.5 to 0.75 the patient asks the learner to rephrase (no unlock, no score);
< 0.5 ignored. T-031 refines this file.
"""

from typing import NamedTuple

from app.ai.interpreter import DetectedAction, Interpretation

ACCEPT = 0.75
CLARIFY = 0.5


class Decision(NamedTuple):
    accepted: tuple[DetectedAction, ...]
    clarify: bool
    candidates: tuple[str, ...]  # ids in the clarification band, for the event log only


def apply_policy(interp: Interpretation) -> Decision:
    accepted = tuple(a for a in interp.actions if a.confidence >= ACCEPT)
    band = tuple(a.id for a in interp.actions if CLARIFY <= a.confidence < ACCEPT)
    # a mixed message keeps what was understood; the patient only asks back when nothing was
    clarify = not accepted and (bool(band) or interp.needs_clarification)
    return Decision(accepted, clarify, band)
