"""LP-01: `mood` is a coarse reaction to a committed choice; nothing else about it leaks."""

from app.ai.providers.mock import MockProvider
from tests.integration.api.conftest import Api, keys_of
from tests.integration.api.test_family_v2_api import Room, use

STORY = "thai-elements-family"
SECRET = {"skills", "safe", "feedback_th", "dimension", "score_total", "flags"}


def test_mood_warm_with_skills_open_without_and_nothing_else_leaks(api: Api) -> None:
    use(api, MockProvider())
    r = Room(api, STORY)
    scene = r.view(r.mother)["scene"]
    assert scene["examples_th"] and len(scene["examples_th"]) == 3
    assert not keys_of(scene["examples_th"])
    assert r.press(r.mother, "continue").status_code == 200
    assert r.press(r.mother, "compare-sources").status_code == 200
    assert r.press(r.mother, "keep-a-menu-list").status_code == 200
    view = r.view(r.mother)
    assert [t["mood"] for t in view["transcript"]] == ["open", "warm", "open"]
    assert view["scene"] is None or view["scene"]["examples_th"] == []
    assert not SECRET & {k for t in view["transcript"] for k in t}
