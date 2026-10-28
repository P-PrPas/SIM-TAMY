"""Knowledge API (contracts section 4): shapes, 404 envelope, and unreleased units stay hidden."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.content.knowledge import cached_knowledge
from app.core.config import get_settings
from app.main import create_app

CONTENT = Path(__file__).resolve().parents[5] / "content"


def _client(monkeypatch: pytest.MonkeyPatch, content: Path) -> TestClient:
    monkeypatch.setenv("CONTENT_DIR", str(content))
    get_settings.cache_clear()
    cached_knowledge.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield _client(monkeypatch, CONTENT)
    get_settings.cache_clear()
    cached_knowledge.cache_clear()


def test_release_reports_id_and_unit_count(client: TestClient) -> None:
    body = client.get("/v1/knowledge/release").json()

    assert set(body) == {"id", "unit_count"}
    assert body["id"].startswith("rel-") and body["unit_count"] >= 10


def test_sources_can_be_filtered_by_kind(client: TestClient) -> None:
    everything = client.get("/v1/knowledge/sources").json()["items"]
    catalog = client.get("/v1/knowledge/sources", params={"kind": "catalog"}).json()["items"]
    kb = client.get("/v1/knowledge/sources", params={"kind": "kb_source"}).json()["items"]

    assert (len(everything), len(catalog), len(kb)) == (135, 84, 51)
    assert set(kb[0]) == {"id", "kind", "title", "publisher", "year", "url", "rights_status"}
    assert client.get("/v1/knowledge/sources", params={"kind": "nope"}).status_code == 422


def test_unit_list_has_the_agreed_shape(client: TestClient) -> None:
    body = client.get("/v1/knowledge/units").json()
    by_id = {i["id"]: i for i in body["items"]}

    assert set(body) == {"release_id", "items"}
    assert set(by_id["KB-TM-SAFE-001"]) == {
        "id",
        "version",
        "title_th",
        "care_stage",
        "domain",
        "has_lens",
    }
    assert by_id["KB-TM-SAFE-001"]["has_lens"] is True
    assert by_id["KB-PP-WARN-001"]["has_lens"] is False
    assert by_id["KB-PP-WARN-001"]["care_stage"] == "postpartum"


def test_unit_detail_resolves_sources_and_lens(client: TestClient) -> None:
    body = client.get("/v1/knowledge/units/KB-TM-HERB-001").json()

    assert set(body) == {
        "id",
        "version",
        "title_th",
        "care_stage",
        "domain",
        "evidence_status",
        "review_basis",
        "reviewed_on",
        "claims",
        "lens",
        "contraindications_th",
        "escalation_th",
    }
    assert body["review_basis"] == "knowledge_base_2026" and body["domain"] == 10
    claim = body["claims"][0]
    assert set(claim) == {"id", "type", "text_th", "sources", "hotspots"}
    assert set(claim["sources"][0]) == {"source_id", "title", "url", "locator"}
    assert claim["sources"][0]["source_id"] == "S23" and "KB 2026" in claim["sources"][0]["locator"]
    assert set(body["lens"]) == {"wisdom_th", "safety_th", "rights_th"}
    plain = client.get("/v1/knowledge/units/KB-PP-WARN-001").json()
    assert plain["lens"] is None and plain["escalation_th"]


def test_unit_detail_exposes_lesson_hotspots(client: TestClient) -> None:
    claims = client.get("/v1/knowledge/units/KB-TM-ELEMENT-001").json()["claims"]

    assert [len(c["hotspots"]) for c in claims] == [5, 2, 3, 6, 5]
    assert set(claims[0]["hotspots"][0]) == {"id", "label_th", "text_th"}
    assert client.get("/v1/knowledge/units/KB-PP-WARN-001").json()["claims"][0]["hotspots"] == []


def test_unknown_unit_is_a_404_envelope(client: TestClient) -> None:
    response = client.get("/v1/knowledge/units/KB-NOPE-NOPE-001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_learning_paths_list_stages_and_objectives(client: TestClient) -> None:
    body = client.get("/v1/learning-paths").json()

    assert body["release_id"] == client.get("/v1/knowledge/release").json()["id"]
    assert [s["stage"] for s in body["stages"]] == [1, 2, 3, 4]
    stage3 = body["stages"][2]
    assert set(stage3) == {"stage", "title_th", "summary_th", "objectives"}
    objective = next(o for o in stage3["objectives"] if o["id"] == "OBJ-3-01")
    assert set(objective) == {"id", "title_th", "dimension", "unit_ids", "story_ids"}
    assert "KB-PP-WARN-001" in objective["unit_ids"]


def test_a_draft_unit_is_not_exposed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    content = tmp_path / "content"
    for name in ("knowledge", "curriculum", "family", "cases"):
        shutil.copytree(CONTENT / name, content / name)
    path = content / "knowledge" / "units" / "KB-BF-HELP-001.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["publish_status"] = "draft"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    # the objective that used it would now dangle, so drop that reference too
    paths = content / "curriculum" / "paths.yaml"
    paths.write_text(
        paths.read_text(encoding="utf-8").replace("[KB-BF-HELP-001]", "[KB-NB-WARN-001]"),
        encoding="utf-8",
    )
    try:
        api = _client(monkeypatch, content)

        listed = {i["id"] for i in api.get("/v1/knowledge/units").json()["items"]}
        assert "KB-BF-HELP-001" not in listed and "KB-NB-WARN-001" in listed
        assert api.get("/v1/knowledge/units/KB-BF-HELP-001").status_code == 404
        assert api.get("/v1/knowledge/release").json()["unit_count"] == len(listed)
    finally:
        get_settings.cache_clear()
        cached_knowledge.cache_clear()
