from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.integrations.posthog.types import PosthogLeadEvent
from src.services.lead_scoring_engine.types import MatchedScoringRule
from src.services.lead_scoring_engine.types import ScoreComputationBreakdown


class LeadBehaviorScorer:
    """Evaluate behavior rules against mocked PostHog event data."""

    def score_lead(
        self,
        *,
        events: list[PosthogLeadEvent],
        rules: list[dict],
        as_of: datetime,
    ) -> ScoreComputationBreakdown:
        """Return behavior score contribution for one lead and its matched rules."""
        matched_rules: list[MatchedScoringRule] = []
        score_delta = 0

        for rule in rules:
            if self._matches_rule(events=events, rule=rule, as_of=as_of):
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

    def _matches_rule(self, *, events: list[PosthogLeadEvent], rule: dict, as_of: datetime) -> bool:
        rule_config = rule["rule_config"]
        matched_event_count = 0
        lookback_boundary = as_of.astimezone(UTC) - timedelta(days=rule_config["lookback_days"])

        for event in events:
            if event.event_name != rule_config["event_name"]:
                continue
            if event.occurred_at < lookback_boundary:
                continue
            if not self._matches_property_filters(
                event_properties=event.event_properties,
                property_filters=rule_config["property_filters"],
            ):
                continue
            matched_event_count += 1

        if rule_config["aggregate_operator"] == "count_gte":
            return matched_event_count >= rule_config["value"]
        if rule_config["aggregate_operator"] == "count_eq":
            return matched_event_count == rule_config["value"]
        return False

    def _matches_property_filters(
        self,
        *,
        event_properties: dict[str, Any],
        property_filters: dict[str, Any],
    ) -> bool:
        for property_name, property_value in property_filters.items():
            if event_properties.get(property_name) != property_value:
                return False
        return True
