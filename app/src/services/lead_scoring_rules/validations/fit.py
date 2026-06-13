from __future__ import annotations

from typing import Any

from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition
from src.services.lead_scoring_rules.validations.base import BaseScoringRuleValidator
from src.services.lead_scoring_rules.validations.helpers import assert_no_unknown_fields
from src.services.lead_scoring_rules.validations.helpers import assert_required_fields


class FitScoringRuleValidator(BaseScoringRuleValidator):
    """Validate fit-rule configs for one resolved contract version."""

    def validate(self, rule_config: dict[str, Any], contract: RuleContractDefinition) -> None:
        """Validate one fit-rule config against a resolved fit contract."""
        assert_required_fields(rule_config, contract)
        assert_no_unknown_fields(rule_config, contract)

        if rule_config["version"] != contract.version:
            self.raise_validation_error(
                "rule_config version does not match resolved contract version",
                field_path="rule_config.version",
                allowed_values=[contract.version],
            )

        field_name = rule_config["field"]
        if not isinstance(field_name, str) or field_name not in contract.allowed_operator_matrix:
            self.raise_validation_error(
                "unsupported fit rule field",
                field_path="rule_config.field",
                allowed_values=list(contract.allowed_operator_matrix.keys()),
            )

        operator = rule_config["operator"]
        allowed_operators = list(contract.allowed_operator_matrix[field_name])
        if not isinstance(operator, str) or operator not in allowed_operators:
            self.raise_validation_error(
                "unsupported operator for fit rule field",
                field_path="rule_config.operator",
                allowed_values=allowed_operators,
            )

        self._validate_value(field_name=field_name, operator=operator, value=rule_config["value"])

    def _validate_value(self, *, field_name: str, operator: str, value: Any) -> None:
        if field_name == "company_size":
            if not isinstance(value, int) or isinstance(value, bool):
                self.raise_validation_error(
                    "company_size comparisons require an integer value",
                    field_path="rule_config.value",
                )
            return

        if operator in ("in", "not_in"):
            if not isinstance(value, list) or len(value) == 0 or not all(isinstance(item, str) for item in value):
                self.raise_validation_error(
                    "set-based fit comparisons require a non-empty string array",
                    field_path="rule_config.value",
                )
            return

        if not isinstance(value, str) or value.strip() == "":
            self.raise_validation_error(
                "fit rule value must be a non-empty string",
                field_path="rule_config.value",
            )
