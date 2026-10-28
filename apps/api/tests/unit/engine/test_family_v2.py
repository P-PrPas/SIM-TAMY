"""2.0 family engine: discover steps, asks, rubric dimensions, replay determinism (section 3).

Covers CT-05 (a role cannot reach the other role's fact), CT-07 (one transition per decision),
CT-10 (an invalid rubric cannot be loaded, so nothing can finalize) and the Golden Scenario paths.
"""

from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.family import load_stories
from app.domain.family import DEFAULT_RUBRIC, FamilyStory
from app.engine.family import FamilyEventRecord as Ev
from app.engine.family import assess, replay, revealing, rubric_score

CONTENT = Path(__file__).resolve().parents[5] / "content"
STORIES = {s.id: s for s in load_stories(CONTENT)}
GS = [STORIES["gs-a-postpartum-warning"], STORIES["gs-b-thai-recovery"]]


def full_log(story: FamilyStory, picks: dict[int, str], *, asks: bool = True) -> list[Ev]:
    """One authored path: discover steps ask every intent, choice steps take `picks[i]` or the
    first choice, joint steps get two matching votes, and revealed facts are all shared."""
    log: list[Ev] = []
    for i, step in enumerate(story.steps):
        if step.kind == "discover":
            if asks:
                log += [Ev("ask", step.role, intent.id, "r") for intent in step.intents]
                log += [Ev("share", step.role, f) for it in step.intents for f in it.reveals]
            log.append(Ev("decision", step.role, "continue"))
            continue
        choice = picks.get(i, step.choices[0].id)
        if step.joint:
            log += [Ev("vote", "mother", choice), Ev("vote", "father", choice)]
        else:
            log.append(Ev("decision", step.role, choice))
    return log


@pytest.mark.parametrize("story", GS, ids=lambda s: s.id)
def test_golden_scenarios_are_staged_coop_drafts_with_shared_ids(story: FamilyStory) -> None:
    assert story.stage == 3 and story.mode == "coop" and story.status == "Draft"
    assert story.objective_ids and story.knowledge_unit_ids
    assert any(s.kind == "discover" for s in story.steps)
    assert {f.role for f in story.facts} == {"mother", "father"}
    assert story.weights == DEFAULT_RUBRIC


def test_gs_a_has_a_joint_critical_step_and_gs_b_has_no_emergency_gate() -> None:
    a, b = GS
    assert any(s.joint and s.critical for s in a.steps)
    assert not any(s.critical for s in b.steps)
    assert (a.objective_ids, b.objective_ids) == (
        ["OBJ-3-01", "OBJ-3-03"],
        ["OBJ-3-02", "OBJ-3-03", "OBJ-3-04"],
    )


@pytest.mark.parametrize("story", GS, ids=lambda s: s.id)
def test_every_branch_completes_and_replays_identically(story: FamilyStory) -> None:
    options = [
        [c.id for c in step.choices] if step.kind == "choice" else ["continue"]
        for step in story.steps
    ]
    count = 0
    for path in product(*options):
        log = full_log(story, dict(enumerate(path)))
        first, again = replay(story, log), replay(story, list(log))
        assert first == again and first.choices == list(path)
        assert assess(story, first.choices, first.facts) == assess(
            story, again.choices, again.facts
        )
        assert rubric_score(story, first) == rubric_score(story, again)
        count += 1
    assert count > 1


def test_ask_reveals_to_the_asking_role_and_a_repeat_does_not_reveal_again() -> None:
    story = GS[0]
    step = story.steps[0]
    first = replay(story, [Ev("ask", "mother", "ASK_BLEEDING", "a")])
    assert first.revealed == {"m-bleed"} and first.events == 1
    again = replay(story, [Ev("ask", "mother", "ASK_BLEEDING", "a")] * 2)
    assert again.revealed == {"m-bleed"} and again.events == 2  # logged, not re-revealed
    assert again.asked(0) == ["ASK_BLEEDING", "ASK_BLEEDING"]
    assert revealing(step, again.asked(0)) == 1  # a repeat does not count twice


def test_ct05_a_role_cannot_ask_the_other_roles_step_or_share_an_unrevealed_fact() -> None:
    story = GS[0]
    with pytest.raises(ValueError):  # father asking in the mother's discover step
        replay(story, [Ev("ask", "father", "ASK_BLEEDING", "a")])
    with pytest.raises(ValueError):  # father cannot share the mother's fact, revealed or not
        replay(story, [Ev("ask", "mother", "ASK_BLEEDING", "a"), Ev("share", "father", "m-bleed")])
    with pytest.raises(ValueError):  # sharing a discoverable fact before it is revealed
        replay(story, [Ev("share", "mother", "m-bleed")])


def test_continue_needs_min_reveals_and_unknown_intents_are_rejected() -> None:
    story = GS[0]
    with pytest.raises(ValueError):
        replay(story, [Ev("decision", "mother", "continue")])
    with pytest.raises(ValueError):
        replay(story, [Ev("ask", "mother", "NOT_AN_INTENT", "a")])
    # an intent that reveals nothing does not satisfy min_reveals
    with pytest.raises(ValueError):
        replay(story, [Ev("ask", "mother", "ASK_PLAN", "a"), Ev("decision", "mother", "continue")])
    ok = replay(
        story, [Ev("ask", "mother", "ASK_CHEST", "a"), Ev("decision", "mother", "continue")]
    )
    assert ok.choices == ["continue"]


def test_ct07_a_decision_locks_exactly_one_step_and_a_second_is_refused() -> None:
    story = GS[1]
    log = [Ev("ask", "mother", "ASK_HEAT", "a"), Ev("decision", "mother", "continue")]
    assert len(replay(story, log).choices) == 1
    with pytest.raises(ValueError):  # the next step belongs to the father
        replay(story, [*log, Ev("decision", "mother", "continue")])


def test_rubric_is_weighted_by_dimension_and_never_mixed_with_the_safety_gate() -> None:
    story = GS[0]
    joint = next(i for i, s in enumerate(story.steps) if s.joint)
    safe = replay(story, full_log(story, {}))
    missed = replay(story, full_log(story, {joint: "wait-until-morning"}))
    good, bad = rubric_score(story, safe), rubric_score(story, missed)
    assert good and bad
    assert good.total > bad.total
    assert {d.id for d in good.dimensions} == set(DEFAULT_RUBRIC)
    assert all(0 <= d.score <= 100 for d in good.dimensions)
    # the gate is its own result: a missed critical step is SAFETY_NOT_MET at any total score
    assert assess(story, safe.choices, safe.facts).safety_met
    assert not assess(story, missed.choices, missed.facts).safety_met
    high = rubric_score(story, replay(story, full_log(story, {joint: "tradition-first"})))
    assert high and high.total >= 50  # a high total cannot turn the gate into a pass


def test_stories_without_stage_or_discover_have_no_rubric_scores() -> None:
    old = STORIES["golden-first-night"]
    assert not old.scored
    assert rubric_score(old, replay(old, [])) is None


def test_ct10_an_invalid_rubric_or_unknown_reference_cannot_load() -> None:
    raw = GS[0].model_dump(mode="json")
    for patch in (
        {"rubric": [{"id": "discovery", "weight": 60}, {"id": "decision", "weight": 20}]},
        {"objective_ids": ["bad"]},
        {"knowledge_unit_ids": ["KB-PP-WARN-1"]},
    ):
        with pytest.raises(ValidationError):
            FamilyStory.model_validate({**raw, **patch})


def test_intents_must_reveal_only_the_askers_own_facts_and_stay_in_scope() -> None:
    raw = GS[0].model_dump(mode="json")
    foreign = {**raw, "steps": [dict(s) for s in raw["steps"]]}
    foreign["steps"][0]["intents"] = [
        {**foreign["steps"][0]["intents"][0], "reveals": ["f-breath"]},
        *foreign["steps"][0]["intents"][1:],
    ]
    with pytest.raises(ValidationError):
        FamilyStory.model_validate(foreign)
    outside = {**raw, "knowledge_unit_ids": ["KB-TM-REST-001"]}
    with pytest.raises(ValidationError):
        FamilyStory.model_validate(outside)
