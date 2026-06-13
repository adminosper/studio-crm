from __future__ import annotations

from typing import Any

from src.shared.exceptions import RuleConfigValidationError
from src.services.lead_scoring_rules.contracts.registry import get_available_rule_contract_versions
from src.services.lead_scoring_rules.contracts.registry import get_rule_contract
from src.services.lead_scoring_rules.contracts.types import RuleType
from src.services.lead_scoring_rules.normalization.rule_config import normalize_existing_rule_config
from src.services.lead_scoring_rules.normalization.rule_config import normalize_rule_config
from src.services.lead_scoring_rules.validations.base import BaseScoringRuleValidator
from src.services.lead_scoring_rules.validations.behavior import BehaviorScoringRuleValidator
from src.services.lead_scoring_rules.validations.fit import FitScoringRuleValidator


class LeadScoringRuleValidationService:
    """Resolve versioned rule contracts, validate configs, and return canonical rule JSON."""

    def __init__(
        self,
        fit_validator: FitScoringRuleValidator,
        behavior_validator: BehaviorScoringRuleValidator,
    ) -> None:
        self._fit_validator = fit_validator
        self._behavior_validator = behavior_validator

    def validate_and_normalize(self, rule_type: RuleType, rule_config: dict[str, Any]) -> dict[str, Any]:
        """Validate a requested rule config and return the canonical stored form."""
        version = rule_config.get("version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise RuleConfigValidationError(
                message="rule_config.version must be an integer",
                field_path="rule_config.version",
            )

        contract = get_rule_contract(rule_type, version)
        if contract is None:
            raise RuleConfigValidationError(
                message="unsupported rule contract version",
                field_path="rule_config.version",
                allowed_values=get_available_rule_contract_versions(rule_type),
            )

        validator = self._resolve_validator(rule_type)
        validator.validate(rule_config=rule_config, contract=contract)
        return normalize_rule_config(rule_type=rule_type, rule_config=rule_config, contract=contract)

    def normalize_persisted_rule_config(self, rule_type: RuleType, rule_config: dict[str, Any]) -> dict[str, Any]:
        """Normalize stored rules, including legacy rows written before config versioning."""
        prepared_config = normalize_existing_rule_config(rule_type=rule_type, rule_config=rule_config)
        return self.validate_and_normalize(rule_type=rule_type, rule_config=prepared_config)

    def _resolve_validator(self, rule_type: RuleType) -> BaseScoringRuleValidator:
        if rule_type == "fit":
            return self._fit_validator
        return self._behavior_validator
