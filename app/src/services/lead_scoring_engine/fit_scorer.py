from __future__ import annotations

from src.services.lead_scoring_engine.types import MatchedScoringRule
from src.services.lead_scoring_engine.types import ScoreComputationBreakdown


class LeadFitScorer:
    """Evaluate tenant fit rules against one lead."""

    def score_lead(self, *, lead: dict, rules: list[dict]) -> ScoreComputationBreakdown:
        """Return fit score contribution for one lead and its matched rules."""
        matched_rules: list[MatchedScoringRule] = []
        score_delta = 0

        for rule in rules:
            if self._matches_rule(lead=lead, rule=rule):
                matched_rules.append(
                    MatchedScoringRule(
                        rule_name=rule["rule_name"],
                        score_delta=rule["score_delta"],
                    )
                )
                score_delta += rule["score_delta"]

        return ScoreComputationBreakdown(
            score_delta=score_delta,
            matched_rules=tuple(matched_rules),
        )

    def _matches_rule(self, *, lead: dict, rule: dict) -> bool:
        rule_config = rule["rule_config"]
        field_name = rule_config["field"]
        operator = rule_config["operator"]
        comparison_value = rule_config["value"]
        lead_value = lead[field_name]

        if operator == "equals":
            return lead_value == comparison_value
        if operator == "not_equals":
            return lead_value != comparison_value
        if operator == "in":
            return lead_value in comparison_value
        if operator == "not_in":
            return lead_value not in comparison_value
        if operator == "gte":
            return lead_value >= comparison_value
        if operator == "lte":
            return lead_value <= comparison_value
        if operator == "contains":
            return str(comparison_value).lower() in str(lead_value).lower()
        return False
