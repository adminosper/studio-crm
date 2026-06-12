from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


FIT_RULE_FIELDS = ("industry", "company_size", "geography", "title", "source")
FIT_RULE_OPERATORS = ("equals", "not_equals", "in", "not_in", "gte", "lte", "contains")
BEHAVIOR_RULE_OPERATORS = ("count_gte", "count_eq")


class FitRuleConfig(BaseModel):
    """Typed configuration for fit-based scoring rules."""

    field: Literal["industry", "company_size", "geography", "title", "source"]
    operator: Literal["equals", "not_equals", "in", "not_in", "gte", "lte", "contains"]
    value: str | int | list[str]


class BehaviorRuleConfig(BaseModel):
    """Typed configuration for behavior-based scoring rules."""

    event_name: str = Field(min_length=1)
    aggregate_operator: Literal["count_gte", "count_eq"]
    value: int = Field(ge=0)
    lookback_days: int | None = Field(default=None, ge=1)
    property_filters: dict[str, Any] = Field(default_factory=dict)


class ScoringRuleMutationRequest(BaseModel):
    """Request payload for creating or updating a scoring rule."""

    model_config = ConfigDict(extra="forbid")

    rule_name: str = Field(min_length=1)
    rule_type: Literal["fit", "behavior"]
    score_delta: int
    is_active: bool = True
    rule_config: FitRuleConfig | BehaviorRuleConfig

    @model_validator(mode="after")
    def validate_rule_type_matches_config(self) -> ScoringRuleMutationRequest:
        """Ensure the request's rule type matches the supplied rule config shape."""
        if self.rule_type == "fit" and not isinstance(self.rule_config, FitRuleConfig):
            raise ValueError("fit rules must use fit rule config")
        if self.rule_type == "behavior" and not isinstance(self.rule_config, BehaviorRuleConfig):
            raise ValueError("behavior rules must use behavior rule config")
        return self


class ScoringRuleResponse(BaseModel):
    """Response payload for scoring rule APIs."""

    id: UUID
    tenant_id: UUID
    rule_name: str
    rule_type: Literal["fit", "behavior"]
    score_delta: int
    is_active: bool
    rule_config: FitRuleConfig | BehaviorRuleConfig
    created_at: datetime
    updated_at: datetime
