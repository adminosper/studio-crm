from __future__ import annotations

from src.services.lead_scoring_engine.fit_scorer import LeadFitScorer


def test_score_lead_returns_sum_and_rule_names_for_matching_fit_rules():
    scorer = LeadFitScorer()

    breakdown = scorer.score_lead(
        lead={
            "industry": "SaaS",
            "company_size": 250,
            "geography": "US",
            "title": "Founder",
            "source": "website",
        },
        rules=[
            {
                "rule_name": "SaaS ICP",
                "score_delta": 20,
                "rule_config": {
                    "field": "industry",
                    "operator": "equals",
                    "value": "SaaS",
                },
            },
            {
                "rule_name": "Mid Market",
                "score_delta": 15,
                "rule_config": {
                    "field": "company_size",
                    "operator": "gte",
                    "value": 200,
                },
            },
        ],
    )

    assert breakdown.score_delta == 35
    assert [matched_rule.rule_name for matched_rule in breakdown.matched_rules] == [
        "SaaS ICP",
        "Mid Market",
    ]


def test_score_lead_returns_zero_when_no_fit_rules_match():
    scorer = LeadFitScorer()

    breakdown = scorer.score_lead(
        lead={
            "industry": "Healthcare",
            "company_size": 50,
            "geography": "UK",
            "title": "Manager",
            "source": "manual",
        },
        rules=[
            {
                "rule_name": "Founder Persona",
                "score_delta": 10,
                "rule_config": {
                    "field": "title",
                    "operator": "contains",
                    "value": "Founder",
                },
            }
        ],
    )

    assert breakdown.score_delta == 0
    assert breakdown.matched_rules == ()
