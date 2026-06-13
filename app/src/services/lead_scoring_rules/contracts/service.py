from __future__ import annotations

from src.services.lead_scoring_rules.contracts.registry import list_rule_contracts
from src.services.lead_scoring_rules.contracts.registry import list_rule_contracts_by_type
from src.services.lead_scoring_rules.contracts.registry import serialize_rule_contract
from src.services.lead_scoring_rules.contracts.types import RuleType


class ScoringRuleContractService:
    """Expose versioned rule contracts to API clients."""

    def list_contracts(self) -> list[dict]:
        """Return all available versioned scoring-rule contracts."""
        return [serialize_rule_contract(contract) for contract in list_rule_contracts()]

    def list_contracts_by_type(self, rule_type: RuleType) -> list[dict]:
        """Return all contract versions for one rule type."""
        return [serialize_rule_contract(contract) for contract in list_rule_contracts_by_type(rule_type)]
