from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.shared.exceptions import RuleConfigValidationError
from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition


class BaseScoringRuleValidator(ABC):
    """Base interface for version-specific scoring-rule validators."""

    @abstractmethod
    def validate(self, rule_config: dict[str, Any], contract: RuleContractDefinition) -> None:
        """Validate a rule config against one resolved contract definition."""

    def raise_validation_error(
        self,
        message: str,
        *,
        field_path: str,
        allowed_values: list[Any] | None = None,
    ) -> None:
        """Raise a typed rule-config validation error."""
        raise RuleConfigValidationError(
            message=message,
            field_path=field_path,
            allowed_values=allowed_values,
        )
