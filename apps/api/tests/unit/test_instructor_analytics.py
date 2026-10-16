"""Synthetic cohort metrics for T-057; scores are read, never recomputed."""

from fastapi.testclient import TestClient

from app.domain.scoring import Scoring
from app.main import app
from app.services.instructor import CohortRecord, analytics_from_records


def _score(total: float, safety: str, risk: float, critical: str) -> Scoring:
    return Scoring.model_validate(
        {
            "safety_status": safety,
            "total_score": total,
            "competencies": [
                {
                    "id": "RISK",
                    "name_th": "Synthetic risk",
                    "weight": 100,
                    "score_pct": risk,
                    "earned": risk,
                    "possible": 100,
                }
            ],
            "items": [
                {
                    "id": "SYN-1",
                    "competency": "RISK",
                    "result": critical,
                    "points": 1,
                    "earned": int(critical == "pass"),
                    "critical": True,
                }
            ],
        }
    )


def test_empty_cohort_has_no_fabricated_rates() -> None:
    result = analytics_from_records("ABC123", [], sessions_active=1)
    assert result.sessions_completed == 0
    assert result.sessions_active == 1
    assert result.avg_total_score is None
    assert result.safety_not_met_rate is None
    assert result.avg_turns is None
    assert result.competency_avg == []
    assert result.critical_item_fail_rates == []


def test_instructor_response_is_private_even_when_unauthorized() -> None:
    response = TestClient(app).get("/v1/instructor/classes")
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"


def test_cohort_uses_only_saved_completed_scores_and_critical_fails() -> None:
    records = [
        CohortRecord(
            "DEV-001", _score(40, "SAFETY_NOT_MET", 30, "fail"), 3, {"SYN-1": "Synthetic critical"}
        ),
        CohortRecord(
            "DEV-001", _score(80, "SAFETY_MET", 70, "pass"), 5, {"SYN-1": "Synthetic critical"}
        ),
    ]
    result = analytics_from_records("ABC123", records, sessions_active=1)
    assert result.sessions_completed == 2
    assert result.avg_total_score == 60
    assert result.safety_not_met_rate == 0.5
    assert result.avg_turns == 4
    assert result.competency_avg[0].avg_pct == 50
    assert result.critical_item_fail_rates[0].item_id == "DEV-001:SYN-1"
    assert result.critical_item_fail_rates[0].fail_rate == 0.5
    assert result.critical_item_fail_rates[0].n == 2
