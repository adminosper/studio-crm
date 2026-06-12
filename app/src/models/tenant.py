from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TenantScoringThresholdsResponse(BaseModel):
    """Tenant scoring thresholds exposed by the core configuration API."""

    id: UUID
    name: str
    mql_score_threshold: int
    sql_score_threshold: int
    created_at: datetime
    deleted_at: datetime | None


class TenantScoringThresholdsUpdateRequest(BaseModel):
    """Request payload for updating tenant scoring thresholds."""

    model_config = ConfigDict(extra="forbid")

    mql_score_threshold: int = Field(ge=0)
    sql_score_threshold: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> TenantScoringThresholdsUpdateRequest:
        """Ensure SQL thresholds cannot be lower than MQL thresholds."""
        if self.sql_score_threshold < self.mql_score_threshold:
            raise ValueError("sql_score_threshold must be greater than or equal to mql_score_threshold")
        return self
