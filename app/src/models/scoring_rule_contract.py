from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class RuleContractFieldDefinitionResponse(BaseModel):
    """One field definition exposed by the scoring-rule contract API."""

    name: str
    field_type: str
    required: bool
    description: str
    allowed_values: list[Any] | None = None
    default_value: Any | None = None


class ScoringRuleContractResponse(BaseModel):
    """Versioned scoring-rule contract payload exposed to API clients."""

    rule_type: Literal["fit", "behavior"]
    version: int
    description: str
    required_fields: list[str]
    optional_fields: list[str]
    field_definitions: list[RuleContractFieldDefinitionResponse]
    allowed_operator_matrix: dict[str, list[str]] | None = None
    example: dict[str, Any]
