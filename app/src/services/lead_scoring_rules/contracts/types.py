from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


RuleType: TypeAlias = Literal["fit", "behavior"]


@dataclass(frozen=True)
class RuleContractFieldDefinition:
    """Internal definition of one rule-config field for a versioned contract."""

    name: str
    field_type: str
    required: bool
    description: str
    allowed_values: tuple[Any, ...] | None = None
    default_value: Any | None = None


@dataclass(frozen=True)
class RuleContractDefinition:
    """Internal versioned rule-contract definition."""

    rule_type: RuleType
    version: int
    description: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    field_definitions: tuple[RuleContractFieldDefinition, ...]
    allowed_operator_matrix: dict[str, tuple[str, ...]] | None
    example: dict[str, Any]
