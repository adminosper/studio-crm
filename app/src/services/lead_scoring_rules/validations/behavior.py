from __future__ import annotations

from typing import Any

from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition
from src.services.lead_scoring_rules.validations.base import BaseScoringRuleValidator
from src.services.lead_scoring_rules.validations.helpers import assert_no_unknown_fields
from src.services.lead_scoring_rules.validations.helpers import assert_required_fields


class BehaviorScoringRuleValidator(BaseScoringRuleValidator):
    """Validate behavior-rule configs for one resolved contract version."""

    def validate(self, rule_config: dict[str, Any], contract: RuleContractDefinition) -> None:
        """Validate one behavior-rule config against a resolved behavior contract."""
        assert_required_fields(rule_config, contract)
        assert_no_unknown_fields(rule_config, contract)

        if rule_config["version"] != contract.version:
            self.raise_validation_error(
                "rule_config version does not match resolved contract version",
                field_path="rule_config.version",
                allowed_values=[contract.version],
            )

        event_name = rule_config["event_name"]
        allowed_event_names = self._get_allowed_values(contract=contract, field_name="event_name")
        if not isinstance(event_name, str) or event_name.strip() == "":
            self.raise_validation_error(
                "behavior rule event_name must be a non-empty string",
                field_path="rule_config.event_name",
            )
        if event_name not in allowed_event_names:
            self.raise_validation_error(
                "unsupported behavior event_name",
                field_path="rule_config.event_name",
                allowed_values=allowed_event_names,
            )

        aggregate_operator = rule_config["aggregate_operator"]
        allowed_operators = self._get_allowed_values(contract=contract, field_name="aggregate_operator")
        if not isinstance(aggregate_operator, str) or aggregate_operator not in allowed_operators:
            self.raise_validation_error(
                "unsupported behavior aggregate operator",
                field_path="rule_config.aggregate_operator",
                allowed_values=allowed_operators,
            )

        value = rule_config["value"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            self.raise_validation_error(
                "behavior rule value must be a non-negative integer",
                field_path="rule_config.value",
            )

        lookback_days = rule_config["lookback_days"]
        if not isinstance(lookback_days, int) or isinstance(lookback_days, bool) or lookback_days < 1:
            self.raise_validation_error(
                "behavior rule lookback_days must be a positive integer",
                field_path="rule_config.lookback_days",
            )

        property_filters = rule_config.get("property_filters")
        if property_filters is not None and not isinstance(property_filters, dict):
            self.raise_validation_error(
                "behavior rule property_filters must be an object when provided",
                field_path="rule_config.property_filters",
            )

    def _get_allowed_values(self, *, contract: RuleContractDefinition, field_name: str) -> list[Any]:
        for field_definition in contract.field_definitions:
            if field_definition.name == field_name:
                return list(field_definition.allowed_values or ())
        return []
