from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ScoringComputeLeadResultResponse(BaseModel):
    """Lead-level result returned by the tenant scoring compute API."""

    lead_id: UUID
    status: str
    previous_score: int
    raw_score: int
    final_score: int
    previous_stage: str
    new_stage: str
    is_stage_manually_overridden: bool
    matched_rule_names: list[str]


class ScoringComputeResponse(BaseModel):
    """Tenant-level summary returned by the scoring compute API."""

    tenant_id: UUID
    processed_lead_count: int
    skipped_lead_count: int
    stage_transition_count: int
    max_possible_score: int
    results: list[ScoringComputeLeadResultResponse]
