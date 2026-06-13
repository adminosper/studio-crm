from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.integrations.posthog.types import PosthogLeadEvent
from src.services.lead_scoring_engine.behavior_scorer import LeadBehaviorScorer


def test_score_lead_matches_behavior_rule_using_lookback_and_property_filters():
    scorer = LeadBehaviorScorer()
    as_of = datetime(2026, 6, 13, 10, 0, tzinfo=UTC)

    breakdown = scorer.score_lead(
        events=[
            PosthogLeadEvent(
                lead_id=uuid4(),
                event_name="pricing_page_viewed",
                event_properties={"page": "pricing"},
                occurred_at=as_of - timedelta(days=2),
            ),
            PosthogLeadEvent(
                lead_id=uuid4(),
                event_name="pricing_page_viewed",
                event_properties={"page": "pricing"},
                occurred_at=as_of - timedelta(days=5),
            ),
        ],
        rules=[
            {
                "rule_name": "Pricing Intent",
                "score_delta": 20,
                "rule_config": {
                    "event_name": "pricing_page_viewed",
                    "aggregate_operator": "count_gte",
                    "value": 2,
                    "lookback_days": 30,
                    "property_filters": {"page": "pricing"},
                },
            }
        ],
        as_of=as_of,
    )

    assert breakdown.score_delta == 20
    assert [matched_rule.rule_name for matched_rule in breakdown.matched_rules] == ["Pricing Intent"]


def test_score_lead_returns_zero_when_behavior_rule_events_do_not_match():
    scorer = LeadBehaviorScorer()
    as_of = datetime(2026, 6, 13, 10, 0, tzinfo=UTC)

    breakdown = scorer.score_lead(
        events=[
            PosthogLeadEvent(
                lead_id=uuid4(),
                event_name="pricing_page_viewed",
                event_properties={"page": "homepage"},
                occurred_at=as_of - timedelta(days=45),
            )
        ],
        rules=[
            {
                "rule_name": "Pricing Intent",
                "score_delta": 20,
                "rule_config": {
                    "event_name": "pricing_page_viewed",
                    "aggregate_operator": "count_gte",
                    "value": 1,
                    "lookback_days": 30,
                    "property_filters": {"page": "pricing"},
                },
            }
        ],
        as_of=as_of,
    )

    assert breakdown.score_delta == 0
    assert breakdown.matched_rules == ()
