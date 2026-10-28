"""S0-04 / S1-01: the shipped source registry, knowledge units and learning paths (CT-01..03)."""

import json
import shutil
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from app.content.knowledge import KnowledgeBase, load_knowledge
from app.content.loader import ContentError

CONTENT = Path(__file__).resolve().parents[5] / "content"
CATALOG = CONTENT.parent / "docs" / "knowledge base" / "Midwifery_Textbook_Catalog_2026.json"

REQUIRED_UNITS = {
    "KB-PP-WARN-001",
    "KB-TM-REST-001",
    "KB-TM-SAFE-001",
    "KB-TM-HERB-001",
    "KB-RIGHTS-SCOPE-001",
    "KB-RIGHTS-CONSENT-001",
    "KB-NB-WARN-001",
    "KB-BF-HELP-001",
    "KB-ANC-PLAN-001",
    "KB-IP-PLAN-001",
}
LENS_UNITS = {"KB-TM-REST-001", "KB-TM-SAFE-001", "KB-TM-HERB-001"}


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return load_knowledge(CONTENT)


def test_catalog_import_has_84_unique_codes_in_the_expected_sections(kb: KnowledgeBase) -> None:
    catalog = [s for s in kb.sources if s.kind == "catalog"]

    assert len(catalog) == 84 and len({s.id for s in catalog}) == 84
    # catalog section S is stored as CSnn so it cannot clash with the KB report's S01-S40
    sections = Counter(s.id[:2] if s.id.startswith("CS") else s.id[0] for s in catalog)
    assert sections == {"M": 26, "CS": 20, "T": 10, "P": 9, "I": 7, "G": 12}
    assert all(s.rights_status == "metadata_only" for s in catalog)


def test_catalog_import_matches_the_catalog_file_and_holds_no_full_text(
    kb: KnowledgeBase,
) -> None:
    records = json.loads(CATALOG.read_text(encoding="utf-8"))["records"]
    by_id = {s.id: s for s in kb.sources}

    for r in records:
        sid = "CS" + r["code"][1:] if r["section"] == "S" else r["code"]
        assert by_id[sid].title == r["title"] and by_id[sid].url == r["url"]
    # metadata only: every field is short, nothing resembling a book's text
    assert max(len(s.model_dump_json()) for s in kb.sources) < 1500


def test_kb_sources_s01_to_s40_are_public_web_references(kb: KnowledgeBase) -> None:
    original_ids = {f"S{i:02d}" for i in range(1, 41)}
    kb_sources = [s for s in kb.sources if s.id in original_ids]

    assert [s.id for s in kb_sources] == [f"S{i:02d}" for i in range(1, 41)]
    assert all(s.rights_status == "public_web" for s in kb_sources)
    assert all(s.url and s.url.startswith("https://") for s in kb_sources)
    assert kb.source("S36") is not None and "WHO" in kb.source("S36").title  # type: ignore[union-attr]


def test_every_required_unit_is_released_with_provenance(kb: KnowledgeBase) -> None:
    assert {u.id for u in kb.release.units} >= REQUIRED_UNITS
    for unit in kb.release.units:
        assert unit.review_basis == "knowledge_base_2026" and unit.reviewed_on == "2026-10-28"
        assert unit.rights_status == "own_summary" and unit.publish_status == "published"
        for claim in unit.claims:
            assert claim.locators and all(
                "KB 2026" in loc.locator or loc.locator for loc in claim.locators
            )
            assert all(kb.source(loc.source_id) for loc in claim.locators)


def test_thai_service_units_carry_the_wisdom_lens(kb: KnowledgeBase) -> None:
    for uid in LENS_UNITS:
        unit = kb.release.unit(uid)
        assert unit is not None and unit.lens is not None
    assert (kb.release.unit("KB-PP-WARN-001") or pytest.fail()).evidence_status == "secondary"


def test_required_learning_objectives_exist_with_the_agreed_units(kb: KnowledgeBase) -> None:
    objectives = {o.id: o for s in kb.paths.stages for o in s.objectives}

    assert [s.stage for s in kb.paths.stages] == [1, 2, 3, 4]
    assert set(objectives["OBJ-3-01"].unit_ids) == {"KB-PP-WARN-001", "KB-TM-SAFE-001"}
    assert set(objectives["OBJ-3-02"].unit_ids) == {
        "KB-TM-REST-001",
        "KB-TM-SAFE-001",
        "KB-RIGHTS-SCOPE-001",
        "KB-RIGHTS-CONSENT-001",
    }
    assert set(objectives["OBJ-3-03"].unit_ids) == {"KB-TM-REST-001", "KB-RIGHTS-CONSENT-001"}
    assert all(
        any(o.id.startswith(f"OBJ-{s.stage}-") for o in s.objectives) for s in kb.paths.stages
    )


def _copy_content(tmp_path: Path) -> Path:
    dest = tmp_path / "content"
    for name in ("knowledge", "curriculum", "family", "cases"):
        shutil.copytree(CONTENT / name, dest / name)
    return dest


def _edit_unit(content: Path, uid: str, **changes: object) -> None:
    path = content / "knowledge" / "units" / f"{uid}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw.update(changes)
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")


def test_unknown_locator_source_is_reported_with_its_file(tmp_path: Path) -> None:
    content = _copy_content(tmp_path)
    path = content / "knowledge" / "units" / "KB-ANC-PLAN-001.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("source_id: S03", "source_id: S99", 1))

    with pytest.raises(ContentError) as info:
        load_knowledge(content)

    assert any(
        i.file.endswith("KB-ANC-PLAN-001.yaml") and "unknown source_id S99" in i.message
        for i in info.value.issues
    )


def test_claim_without_locator_and_wrong_file_name_are_rejected(tmp_path: Path) -> None:
    content = _copy_content(tmp_path)
    units = content / "knowledge" / "units"
    raw = yaml.safe_load((units / "KB-ANC-PLAN-001.yaml").read_text(encoding="utf-8"))
    raw["claims"][0]["locators"] = []
    (units / "KB-ANC-PLAN-001.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), "utf-8")
    (units / "KB-IP-PLAN-001.yaml").rename(units / "KB-IP-PLAN-009.yaml")

    with pytest.raises(ContentError) as info:
        load_knowledge(content)

    messages = [str(i) for i in info.value.issues]
    assert any("KB-ANC-PLAN-001.yaml: claims.0.locators" in m for m in messages)
    assert any(
        "KB-IP-PLAN-009.yaml: id: file name must be KB-IP-PLAN-001.yaml" in m for m in messages
    )


@pytest.mark.parametrize(
    ("changes", "released"),
    [
        ({"publish_status": "draft"}, False),  # CT-02: unpublished claims never reach production
        ({"publish_status": "retired"}, False),  # AI-T08: retired versions leave the release
        ({"rights_status": "metadata_only"}, False),  # AI-T07: catalog-only claims are blocked
        ({"rights_status": "unknown"}, False),
        ({"title_th": "ชื่อใหม่"}, True),
    ],
)
def test_release_excludes_draft_retired_and_rights_blocked_units(
    tmp_path: Path, changes: dict[str, str], released: bool
) -> None:
    content = _copy_content(tmp_path)
    before = load_knowledge(content)
    _edit_unit(content, "KB-BF-HELP-001", **changes)
    paths = content / "curriculum" / "paths.yaml"  # objectives may only name released units
    paths.write_text(
        paths.read_text(encoding="utf-8").replace("[KB-BF-HELP-001]", "[KB-NB-WARN-001]"),
        encoding="utf-8",
    )

    after = load_knowledge(content)

    assert (after.release.unit("KB-BF-HELP-001") is not None) is released
    assert len(after.units) == len(before.units)  # still on disk, just not released
    assert after.release.id != before.release.id


def test_path_referencing_an_unreleased_unit_or_unknown_story_fails(tmp_path: Path) -> None:
    content = _copy_content(tmp_path)
    _edit_unit(content, "KB-NB-WARN-001", publish_status="draft")
    paths = content / "curriculum" / "paths.yaml"
    paths.write_text(
        paths.read_text(encoding="utf-8").replace("[bridge-herbs]", "[no-such-story]"),
        encoding="utf-8",
    )

    with pytest.raises(ContentError) as info:
        load_knowledge(content)

    messages = [i.message for i in info.value.issues]
    assert "unit KB-NB-WARN-001 is not in the release" in messages
    assert "story or case no-such-story does not exist" in messages


def test_family_story_references_to_units_and_objectives_are_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stream B adds `knowledge_unit_ids` / `objective_ids` to FamilyStory; read defensively."""
    from app.content import knowledge as module
    from app.content.loader import Issue

    story = SimpleNamespace(
        id="x", knowledge_unit_ids=["KB-NOPE-NOPE-001"], objective_ids=["OBJ-9-99"]
    )
    plain = SimpleNamespace(id="y")  # a story without the new fields stays valid
    kb = load_knowledge(CONTENT)
    real = module.load_stories(CONTENT)
    monkeypatch.setattr(module, "load_stories", lambda _d: [*real, story, plain])
    issues: list[Issue] = []

    module._check_references(CONTENT, kb.paths, kb.release, issues)

    assert [(i.file, i.path) for i in issues] == [
        ("family/x.yaml", "knowledge_unit_ids"),
        ("family/x.yaml", "objective_ids"),
    ]
