"""Joint votes, shared facts and the golden story replay deterministically from events alone."""

from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.family import load_stories
from app.domain.family import FamilyStory
from app.engine.family import FamilyEventRecord as Ev
from app.engine.family import assess, prompt, replay

STORIES = {s.id: s for s in load_stories(Path(__file__).resolve().parents[5] / "content")}
GOLDEN = STORIES["golden-first-night"]
JOINT = next(i for i, step in enumerate(GOLDEN.steps) if step.joint)


def play(choice_ids: list[str], shares: tuple[tuple[str, str], ...] = ()) -> list[Ev]:
    """Authored path as events: facts first, then decisions; joint steps get two matching votes."""
    log = [Ev("share", role, fact) for role, fact in shares]  # type: ignore[arg-type]
    for step, choice in zip(GOLDEN.steps, choice_ids, strict=False):
        if step.joint:
            log += [Ev("vote", "mother", choice), Ev("vote", "father", choice)]
        else:
            log.append(Ev("decision", step.role, choice))
    return log


def test_golden_story_is_a_draft_coop_with_joint_critical_step_and_a_card():
    assert GOLDEN.status == "Draft" and GOLDEN.mode == "coop"
    assert 5 <= len(GOLDEN.steps) <= 7
    assert GOLDEN.steps[JOINT].critical
    assert any(step.card and step.card.precautions_th for step in GOLDEN.steps)
    assert {fact.role for fact in GOLDEN.facts} == {"mother", "father"}


def test_every_golden_branch_completes_with_an_independent_safety_gate():
    options = [tuple(c.id for c in step.choices) for step in GOLDEN.steps]
    count = 0
    for path in product(*options):
        state = replay(GOLDEN, play(list(path)))
        assert state.choices == list(path)
        result = assess(GOLDEN, state.choices, state.facts)
        assert result.safety_met == (path[JOINT] == GOLDEN.steps[JOINT].choices[0].id)
        assert prompt(GOLDEN, state.choices) == ""
        count += 1
    assert count == 2 * 2 * 3 * 3 * 2 * 2


def test_good_and_missed_information_branches_differ_but_both_complete():
    good = ["say-what-you-see", "share-and-listen", "listen-then-ask", "contact-health-service"]
    missed = ["say-fine", "downplay", "defer-to-elder", "wait-until-morning"]
    tail = ["report-observations", "agree-share-and-ask"]
    facts = (("mother", "m-feed"), ("father", "f-nappy"))
    best = replay(GOLDEN, play(good + tail, facts))
    worst = replay(GOLDEN, play(missed + ["leave-it-to-other", "agree-vaguely"]))
    assert assess(GOLDEN, best.choices, best.facts).safety_met
    assert not assess(GOLDEN, worst.choices, worst.facts).safety_met
    shared_decision = assess(GOLDEN, best.choices, best.facts).competencies["shared_decision"]
    assert shared_decision == (2 + 2, 4 + 2)  # two facts + two choices of six possible
    assert assess(GOLDEN, worst.choices, worst.facts).competencies["shared_decision"] == (0, 6)
    assert prompt(GOLDEN, good[:2], best.facts) != prompt(GOLDEN, good[:2])  # shared info recalled
    assert prompt(GOLDEN, good[:2], ["m-feed"]) == GOLDEN.steps[2].prompt_if["fact:m-feed"]


def test_votes_match_lock_and_mismatch_reopens_without_randomness():
    pre = play(["say-what-you-see", "share-and-listen", "listen-then-ask", "x"])[:-2]
    mismatch = [*pre, Ev("vote", "father", "wait-until-morning")]
    state = replay(GOLDEN, mismatch)
    assert state.version == len(pre)  # one pending vote does not move the optimistic version
    assert state.votes == {"father": "wait-until-morning"}
    state = replay(GOLDEN, [*mismatch, Ev("vote", "mother", "contact-health-service")])
    assert len(state.choices) == JOINT and state.split == {
        "father": "wait-until-morning",
        "mother": "contact-health-service",
    }
    assert state.votes == {} and state.version == len(pre) + 2
    again = [*mismatch, Ev("vote", "mother", "contact-health-service")]
    again += [
        Ev("vote", "mother", "contact-health-service"),
        Ev("vote", "father", "contact-health-service"),
    ]
    state = replay(GOLDEN, again)
    assert state.choices[-1] == "contact-health-service" and state.split is None
    assert replay(GOLDEN, again) == state  # same events, same state


def test_invalid_event_sequences_fail_closed():
    pre = play(["say-what-you-see", "share-and-listen", "listen-then-ask", "x"])[:-2]
    bad_logs = [
        [*pre, Ev("vote", "mother", "wait-until-morning"), Ev("vote", "mother", "argue")],
        [Ev("vote", "mother", "say-fine")],  # vote on a non-joint step
        [Ev("decision", "father", "say-fine")],  # out of turn
        [Ev("share", "father", "m-feed")],  # another role's private fact
        [Ev("share", "mother", "unknown")],
        [Ev("noise", "mother", "say-fine")],
    ]
    for log in bad_logs:
        with pytest.raises(ValueError):
            replay(GOLDEN, log)


def test_resharing_is_idempotent_and_jointless_stories_keep_four_skills():
    state = replay(GOLDEN, [Ev("share", "mother", "m-feed"), Ev("share", "mother", "m-feed")])
    assert state.shared == [("mother", "m-feed")]
    first = STORIES["first-night"]
    log = ["ask-rest", "share-load", "trusted-backup", "contact-professional"]
    assert set(assess(first, log).competencies) == {
        "communication",
        "responsibility",
        "safety",
        "support",
    }


def test_schema_is_backward_compatible_and_rejects_bad_new_references():
    for story in STORIES.values():
        assert FamilyStory.model_validate(story.model_dump(mode="json")) == story
        if story.id != GOLDEN.id:
            assert not story.facts and not any(step.joint for step in story.steps)
    raw = GOLDEN.model_dump(mode="json")
    for mutate in (
        lambda r: r["steps"][2]["prompt_if"].update({"fact:missing": "x"}),
        lambda r: r["steps"][2]["card"].update({"source_ids": ["missing"]}),
        lambda r: r["facts"].append(dict(r["facts"][0])),
        lambda r: r.update(mode="solo"),
    ):
        copy = FamilyStory.model_validate(raw).model_dump(mode="json")
        mutate(copy)
        with pytest.raises(ValidationError):
            FamilyStory.model_validate(copy)


def test_bridge_cards_are_structured_and_sourced():
    for topic in ("fire", "compress", "food", "herbs"):
        card = STORIES[f"bridge-{topic}"].steps[0].card
        assert card and card.precautions_th and card.when_to_consult_th
        assert card.evidence_status in {"traditional_practice", "insufficient_evidence", "caution"}
