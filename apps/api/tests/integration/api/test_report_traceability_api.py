"""A05: every score and critical flag traces to session, case version, rubric version and events."""

from tests.integration.api.conftest import Api
from tests.integration.api.test_closing_api import complete, play, report


def test_the_report_names_its_versions_and_every_verdict_cites_timeline_events(api: Api) -> None:
    created = play(api)
    complete(api, created)

    body = report(api, created).json()

    assert body["session_id"] == created["session_id"]
    assert body["case"]["version"] == api.loaded.case.version
    assert body["case"]["hash"] == api.loaded.case_hash
    assert body["rubric_version"] == api.loaded.rubric.rubric_version
    timeline_ids = {t["event_id"] for t in body["timeline"]}
    scored = [i for i in body["items"] if i["result"] in ("pass", "fail")]
    assert scored
    for item in scored:
        assert item["evidence"], item["id"]
        assert {e["event_id"] for e in item["evidence"]} <= timeline_ids
