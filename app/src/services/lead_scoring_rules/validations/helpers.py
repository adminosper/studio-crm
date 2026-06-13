from __future__ import annotations

from src.shared.exceptions import RuleConfigValidationError
from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition


def assert_required_fields(rule_config: dict[str, object], contract: RuleContractDefinition) -> None:
    """Ensure all required fields for the resolved contract are present."""
    for field_name in contract.required_fields:
        if field_name not in rule_config:
            raise RuleConfigValidationError(
                message="required rule_config field is missing",
                field_path=f"rule_config.{field_name}",
            )


def assert_no_unknown_fields(rule_config: dict[str, object], contract: RuleContractDefinition) -> None:
    """Ensure rule_config contains only fields declared by the resolved contract."""
    allowed_field_names = set(contract.required_fields) | set(contract.optional_fields)
    for field_name in rule_config.keys():
        if field_name not in allowed_field_names:
            raise RuleConfigValidationError(
                message="unknown rule_config field",
                field_path=f"rule_config.{field_name}",
                allowed_values=sorted(allowed_field_names),
            )
