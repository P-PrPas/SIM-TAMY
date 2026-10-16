"""T-073: Replay reads static snapshots only, with no DB or LLM dependency."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.content.loader import load_case
from app.core.config import get_settings
from app.engine.scoring import score
from app.main import create_app
from tests.unit.engine.play import Play


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_REPLAY", "true")
    get_settings.cache_clear()
    yield TestClient(create_app(), raise_server_exceptions=False), tmp_path
    get_settings.cache_clear()


def _recording() -> dict:
    return {
        "recording_id": "dev-001",
        "title_th": "Synthetic engineering replay",
        "case_id": "DEV-001",
        "variant": "A",
        "description_th": "Engineering only",
        "steps_count": 2,
        "case": {
            "case_id": "DEV-001",
            "version": "0.1",
            "title_th": "Synthetic engineering case",
            "status": "Draft",
            "status_label_th": "Draft",
            "variants_available": ["A"],
            "patient_display_th": "Synthetic patient",
            "learning_objectives": [],
            "decision_options": [],
            "disclaimer_th": "Education only",
        },
        "steps": [
            {"t_ms": 0, "type": "learner", "speaker": "learner", "text": "Hello"},
            {"t_ms": 250, "type": "complete"},
        ],
        "report": {
            "session_id": "00000000-0000-0000-0000-000000000001",
            "generated_at": "2026-10-16T00:00:00Z",
            "engine_version": "0.1.0",
            "rubric_version": "0.1",
            "variant": "A",
            "safety_status": "SAFETY_NOT_MET",
            "total_score": 0,
            "competencies": [],
            "items": [],
            "findings": [],
            "debrief": {"source": "template", "paragraphs": []},
            "timeline": [],
            "glassbox": {"facts": [], "risk_state_timeline": [], "learner_actions": []},
            "replay": {
                "terminal_state": "COMPLETED",
                "timeline_th": [],
                "missed_opportunities": [],
                "disclaimer_th": "Education only",
            },
            "references": [],
            "overrides": [],
            "effective": {"safety_status": "SAFETY_NOT_MET", "total_score": 0},
            "disclaimers": ["Education only"],
            "case": {
                "case_id": "DEV-001",
                "version": "0.1",
                "hash": "fixture",
                "status": "Draft",
                "status_label_th": "Draft",
                "title_th": "Synthetic engineering case",
            },
        },
    }


def test_replay_disabled_is_not_found_for_both_endpoints(client, monkeypatch):
    http, folder = client
    (folder / "dev-001.json").write_text(json.dumps(_recording()), encoding="utf-8")
    monkeypatch.setenv("ENABLE_REPLAY", "false")
    get_settings.cache_clear()
    for path in ("/v1/replay/recordings", "/v1/replay/recordings/dev-001"):
        response = http.get(path)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


def test_replay_lists_and_returns_valid_recording_without_llm_or_db(client):
    http, folder = client
    snapshot = _recording()
    (folder / "dev-001.json").write_text(json.dumps(snapshot), encoding="utf-8")
    listing = http.get("/v1/replay/recordings")
    assert listing.status_code == 200
    assert listing.json() == {
        "items": [
            {
                **{
                    key: snapshot[key]
                    for key in (
                        "recording_id",
                        "title_th",
                        "case_id",
                        "variant",
                        "description_th",
                        "steps_count",
                    )
                },
                "status": "Draft",
                "status_label_th": "Draft",
            }
        ]
    }
    detail = http.get("/v1/replay/recordings/dev-001")
    assert detail.status_code == 200
    assert detail.json()["steps"] == snapshot["steps"]
    assert detail.json()["report"]["effective"]["safety_status"] == "SAFETY_NOT_MET"


@pytest.mark.parametrize("name", ["..", "%2e%2e", "missing", ".hidden"])
def test_replay_rejects_unknown_or_unsafe_ids(client, name):
    http, _ = client
    response = http.get(f"/v1/replay/recordings/{name}")
    assert response.status_code == 404


def test_replay_skips_malformed_snapshot_and_rejects_its_detail(client):
    http, folder = client
    (folder / "bad.json").write_text('{"steps": "invalid"}', encoding="utf-8")
    assert http.get("/v1/replay/recordings").json() == {"items": []}
    assert http.get("/v1/replay/recordings/bad").status_code == 404


def test_checked_in_engineering_recording_uses_deterministic_engine(client, monkeypatch):
    http, _ = client
    root = Path(__file__).resolve().parents[4]
    monkeypatch.setenv("RECORDINGS_DIR", str(root / "recordings"))
    get_settings.cache_clear()
    response = http.get("/v1/replay/recordings/dev001-engineering")
    assert response.status_code == 200
    snapshot = response.json()
    loaded = load_case(root / "content" / "cases" / "DEV-001")
    play = Play(loaded, "A").turn("A01", "A02").turn("A03", "A04")
    play.turn("C01", "C02").decide("refer").note(30).complete()
    scored = score(play.events, loaded.rubric, loaded.actions, "A")
    assert snapshot["case_id"] == "DEV-001"
    assert snapshot["report"]["safety_status"] == scored.safety_status
    assert snapshot["report"]["total_score"] == scored.total_score
    assert snapshot["steps_count"] == len(snapshot["steps"])
