from __future__ import annotations

from src.services.lead_scoring_engine.qualification import LeadQualificationService


def test_derive_stage_returns_sql_when_score_meets_sql_threshold():
    service = LeadQualificationService()

    stage = service.derive_stage(
        score=80,
        mql_score_threshold=40,
        sql_score_threshold=70,
    )

    assert stage == "sql"


def test_derive_stage_returns_pre_mql_when_score_is_below_mql_threshold():
    service = LeadQualificationService()

    stage = service.derive_stage(
        score=20,
        mql_score_threshold=40,
        sql_score_threshold=70,
    )

    assert stage == "pre_mql"
