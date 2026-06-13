from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class PosthogLeadEvent:
    """One mocked PostHog event resolved into the local lead-scoring domain."""

    lead_id: UUID
    event_name: str
    event_properties: dict[str, Any]
    occurred_at: datetime
