"""Cross-stream checks using the released knowledge base, not an injected resolver."""

from app.ai.evidence import current_release_id, evidence_pack
from app.content.family import load_stories
from app.content.knowledge import load_knowledge
from app.core.config import get_settings


def test_golden_stories_receive_claims_from_the_pinned_release() -> None:
    content_dir = get_settings().content_dir
    release = load_knowledge(content_dir).release
    assert current_release_id() == release.id
    for story in load_stories(content_dir):
        if not story.id.startswith("gs-"):
            continue
        pack = evidence_pack(story, story.steps[0], "mother", [], release_id=release.id)
        assert pack.release_id == release.id
        assert pack.items
        assert all(item.knowledge_id in story.knowledge_unit_ids for item in pack.items)


def test_golden_objectives_link_back_to_both_stories() -> None:
    content_dir = get_settings().content_dir
    paths = load_knowledge(content_dir).paths
    objectives = {obj.id: obj for stage in paths.stages for obj in stage.objectives}
    stories = [s for s in load_stories(content_dir) if s.id.startswith("gs-")]
    assert len(stories) == 2
    for story in stories:
        assert story.objective_ids
        for objective_id in story.objective_ids:
            assert story.id in objectives[objective_id].story_ids
