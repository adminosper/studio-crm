from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LeadResponse(BaseModel):
    """Lead payload returned by the core read APIs."""

    id: UUID
    tenant_id: UUID
    name: str
    email: str
    company: str
    industry: str
    company_size: int
    geography: str
    phone: str
    title: str
    source: str
    status: str
    stage: str
    score: int
    score_last_updated_at: datetime | None
    is_stage_manually_overridden: bool
    created_at: datetime
    updated_at: datetime
