from __future__ import annotations

from typing import Any

from src.services.lead_scoring_rules.contracts.types import RuleContractDefinition
from src.services.lead_scoring_rules.contracts.types import RuleContractFieldDefinition
from src.services.lead_scoring_rules.contracts.types import RuleType

FIT_ALLOWED_OPERATOR_MATRIX = {
    "industry": ("equals", "not_equals", "in", "not_in"),
    "geography": ("equals", "not_equals", "in", "not_in"),
    "source": ("equals", "not_equals", "in", "not_in"),
    "title": ("equals", "not_equals", "in", "not_in", "contains"),
    "company_size": ("equals", "not_equals", "gte", "lte"),
}

FIT_RULE_V1 = RuleContractDefinition(
    rule_type="fit",
    version=1,
    description="Static lead-attribute scoring contract for V1.",
    required_fields=("version", "field", "operator", "value"),
    optional_fields=(),
    field_definitions=(
        RuleContractFieldDefinition(
            name="version",
            field_type="integer",
            required=True,
            description="Contract version for the rule config.",
            allowed_values=(1,),
        ),
        RuleContractFieldDefinition(
            name="field",
            field_type="string",
            required=True,
            description="Lead field used by the fit rule.",
            allowed_values=tuple(FIT_ALLOWED_OPERATOR_MATRIX.keys()),
        ),
        RuleContractFieldDefinition(
            name="operator",
            field_type="string",
            required=True,
            description="Comparison operator allowed for the selected field.",
            allowed_values=tuple(sorted({operator for operators in FIT_ALLOWED_OPERATOR_MATRIX.values() for operator in operators})),
        ),
        RuleContractFieldDefinition(
            name="value",
            field_type="string | integer | string[]",
            required=True,
            description="Comparison value used by the selected field and operator.",
        ),
    ),
    allowed_operator_matrix=FIT_ALLOWED_OPERATOR_MATRIX,
    example={
        "version": 1,
        "field": "industry",
        "operator": "in",
        "value": ["SaaS", "FinTech"],
    },
)

BEHAVIOR_RULE_V1 = RuleContractDefinition(
    rule_type="behavior",
    version=1,
    description="Behavioral event-count scoring contract for V1.",
    required_fields=("version", "event_name", "aggregate_operator", "value", "lookback_days"),
    optional_fields=("property_filters",),
    field_definitions=(
        RuleContractFieldDefinition(
            name="version",
            field_type="integer",
            required=True,
            description="Contract version for the rule config.",
            allowed_values=(1,),
        ),
        RuleContractFieldDefinition(
            name="event_name",
            field_type="string",
            required=True,
            description="Event name to aggregate over the lead event stream.",
        ),
        RuleContractFieldDefinition(
            name="aggregate_operator",
            field_type="string",
            required=True,
            description="Aggregation operator used against the counted events.",
            allowed_values=("count_gte", "count_eq"),
        ),
        RuleContractFieldDefinition(
            name="value",
            field_type="integer",
            required=True,
            description="Threshold count value applied to the aggregate operator.",
        ),
        RuleContractFieldDefinition(
            name="lookback_days",
            field_type="integer",
            required=True,
            description="Number of days in the event lookback window.",
        ),
        RuleContractFieldDefinition(
            name="property_filters",
            field_type="object",
            required=False,
            description="Optional event-property equality filters.",
            default_value={},
        ),
    ),
    allowed_operator_matrix=None,
    example={
        "version": 1,
        "event_name": "pricing_page_viewed",
        "aggregate_operator": "count_gte",
        "value": 2,
        "lookback_days": 30,
        "property_filters": {"page": "pricing"},
    },
)

SCORING_RULE_CONTRACTS: dict[RuleType, dict[int, RuleContractDefinition]] = {
    "fit": {1: FIT_RULE_V1},
    "behavior": {1: BEHAVIOR_RULE_V1},
}


def list_rule_contracts() -> list[RuleContractDefinition]:
    """Return all available scoring-rule contracts ordered by type and version."""
    ordered_contracts: list[RuleContractDefinition] = []
    for rule_type in ("behavior", "fit"):
        ordered_contracts.extend(list_rule_contracts_by_type(rule_type))
    return ordered_contracts


def list_rule_contracts_by_type(rule_type: RuleType) -> list[RuleContractDefinition]:
    """Return all contract versions for one rule type."""
    return [SCORING_RULE_CONTRACTS[rule_type][version] for version in sorted(SCORING_RULE_CONTRACTS[rule_type].keys())]


def get_rule_contract(rule_type: RuleType, version: int) -> RuleContractDefinition | None:
    """Return the contract for one rule type/version pair if it exists."""
    return SCORING_RULE_CONTRACTS.get(rule_type, {}).get(version)


def get_available_rule_contract_versions(rule_type: RuleType) -> list[int]:
    """Return all supported versions for one rule type."""
    return sorted(SCORING_RULE_CONTRACTS.get(rule_type, {}).keys())


def serialize_rule_contract(contract: RuleContractDefinition) -> dict[str, Any]:
    """Convert an internal contract definition into an API-facing payload."""
    return {
        "rule_type": contract.rule_type,
        "version": contract.version,
        "description": contract.description,
        "required_fields": list(contract.required_fields),
        "optional_fields": list(contract.optional_fields),
        "field_definitions": [
            {
                "name": field_definition.name,
                "field_type": field_definition.field_type,
                "required": field_definition.required,
                "description": field_definition.description,
                "allowed_values": list(field_definition.allowed_values) if field_definition.allowed_values is not None else None,
                "default_value": field_definition.default_value,
            }
            for field_definition in contract.field_definitions
        ],
        "allowed_operator_matrix": (
            {field_name: list(operators) for field_name, operators in contract.allowed_operator_matrix.items()}
            if contract.allowed_operator_matrix is not None
            else None
        ),
        "example": contract.example,
    }
