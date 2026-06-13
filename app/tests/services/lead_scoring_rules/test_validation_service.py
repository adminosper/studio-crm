from __future__ import annotations

import pytest

from src.shared.exceptions import RuleConfigValidationError
from src.services.lead_scoring_rules.validations.behavior import BehaviorScoringRuleValidator
from src.services.lead_scoring_rules.validations.fit import FitScoringRuleValidator
from src.services.lead_scoring_rules.validations.service import LeadScoringRuleValidationService


def _build_validation_service() -> LeadScoringRuleValidationService:
    return LeadScoringRuleValidationService(
        fit_validator=FitScoringRuleValidator(),
        behavior_validator=BehaviorScoringRuleValidator(),
    )


def test_validate_and_normalize_behavior_rule_adds_empty_property_filters():
    validation_service = _build_validation_service()

    normalized_rule_config = validation_service.validate_and_normalize(
        rule_type="behavior",
        rule_config={
            "version": 1,
            "event_name": "pricing_page_viewed",
            "aggregate_operator": "count_gte",
            "value": 2,
            "lookback_days": 30,
        },
    )

    assert normalized_rule_config["property_filters"] == {}


def test_validate_and_normalize_rejects_invalid_fit_operator_for_field():
    validation_service = _build_validation_service()

    with pytest.raises(RuleConfigValidationError) as exc_info:
        validation_service.validate_and_normalize(
            rule_type="fit",
            rule_config={
                "version": 1,
                "field": "company_size",
                "operator": "contains",
                "value": 200,
            },
        )

    assert exc_info.value.field_path == "rule_config.operator"


def test_validate_and_normalize_rejects_behavior_rule_without_lookback_days():
    validation_service = _build_validation_service()

    with pytest.raises(RuleConfigValidationError) as exc_info:
        validation_service.validate_and_normalize(
            rule_type="behavior",
            rule_config={
                "version": 1,
                "event_name": "demo_requested",
                "aggregate_operator": "count_gte",
                "value": 1,
            },
        )

    assert exc_info.value.field_path == "rule_config.lookback_days"


def test_validate_and_normalize_rejects_unknown_behavior_event_name():
    validation_service = _build_validation_service()

    with pytest.raises(RuleConfigValidationError) as exc_info:
        validation_service.validate_and_normalize(
            rule_type="behavior",
            rule_config={
                "version": 1,
                "event_name": "unknown_event_name",
                "aggregate_operator": "count_gte",
                "value": 1,
                "lookback_days": 30,
            },
        )

    assert exc_info.value.field_path == "rule_config.event_name"
    assert "pricing_page_viewed" in (exc_info.value.allowed_values or [])


def test_normalize_persisted_rule_config_upgrades_legacy_behavior_rule():
    validation_service = _build_validation_service()

    normalized_rule_config = validation_service.normalize_persisted_rule_config(
        rule_type="behavior",
        rule_config={
            "event_name": "pricing_page_viewed",
            "aggregate_operator": "count_gte",
            "value": 2,
            "lookback_days": 30,
        },
    )

    assert normalized_rule_config["version"] == 1
    assert normalized_rule_config["property_filters"] == {}
