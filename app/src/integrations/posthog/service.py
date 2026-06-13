from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.integrations.posthog.mock_service import MockPosthogService
from src.integrations.posthog.types import PosthogLeadEvent


class PosthogService:
    """Application-facing boundary for PostHog-backed behavioral data access."""

    def __init__(self, mock_service: MockPosthogService) -> None:
        self._mock_service = mock_service

    def load_tenant_events_grouped_by_lead(
        self,
        *,
        tenant_id: UUID,
        lookback_days: int,
        as_of: datetime,
    ) -> dict[UUID, list[PosthogLeadEvent]]:
        """Return behavioral event data for one tenant using the configured implementation."""
        return self._mock_service.load_tenant_events_grouped_by_lead(
            tenant_id=tenant_id,
            lookback_days=lookback_days,
            as_of=as_of,
        )
