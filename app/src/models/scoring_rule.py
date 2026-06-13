from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RuleConfigPayload(BaseModel):
    """Versioned rule config envelope. Version-specific semantics are validated later."""

    model_config = ConfigDict(extra="allow")

    version: int = Field(ge=1)


class ScoringRuleMutationRequest(BaseModel):
    """Request payload for creating or updating a scoring rule."""

    model_config = ConfigDict(extra="forbid")

    rule_name: str = Field(min_length=1)
    rule_type: Literal["fit", "behavior"]
    score_delta: int
    is_active: bool = True
    rule_config: RuleConfigPayload


class ScoringRuleResponse(BaseModel):
    """Response payload for scoring rule APIs."""

    id: UUID
    tenant_id: UUID
    rule_name: str
    rule_type: Literal["fit", "behavior"]
    score_delta: int
    is_active: bool
    rule_config: RuleConfigPayload
    created_at: datetime
    updated_at: datetime
