from __future__ import annotations

from typing import Any

from src.shared.exceptions import RuleConfigValidationError
from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition
from src.services.lead_scoring_rules.contracts.types import RuleType


def normalize_rule_config(rule_type: RuleType, rule_config: dict[str, Any], contract: RuleContractDefinition) -> dict[str, Any]:
    """Normalize a validated rule config into one canonical stored representation."""
    if rule_type == "fit" and contract.version == 1:
        return {
            "version": int(rule_config["version"]),
            "field": rule_config["field"],
            "operator": rule_config["operator"],
            "value": list(rule_config["value"]) if isinstance(rule_config["value"], list) else rule_config["value"],
        }
    if rule_type == "behavior" and contract.version == 1:
        return {
            "version": int(rule_config["version"]),
            "event_name": rule_config["event_name"],
            "aggregate_operator": rule_config["aggregate_operator"],
            "value": int(rule_config["value"]),
            "lookback_days": int(rule_config["lookback_days"]),
            "property_filters": dict(rule_config.get("property_filters", {})),
        }
    raise RuleConfigValidationError(
        message="unsupported rule contract for normalization",
        field_path="rule_config.version",
    )


def normalize_existing_rule_config(rule_type: RuleType, rule_config: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy persisted rule configs to the current canonical representation."""
    normalized_config = dict(rule_config)
    if "version" not in normalized_config:
        normalized_config["version"] = 1
    if rule_type == "behavior" and "property_filters" not in normalized_config:
        normalized_config["property_filters"] = {}
    return normalized_config
