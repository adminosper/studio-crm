from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.integrations.posthog.types import PosthogLeadEvent
from src.repositories.lead_event_repository import LeadEventRepository


class MockPosthogService:
    """Load mocked PostHog behavioral data from local PostgreSQL tables."""

    def __init__(self, lead_event_repository: LeadEventRepository) -> None:
        self._lead_event_repository = lead_event_repository

    def load_tenant_events_grouped_by_lead(
        self,
        *,
        tenant_id: UUID,
        lookback_days: int,
        as_of: datetime,
    ) -> dict[UUID, list[PosthogLeadEvent]]:
        """Return tenant event rows grouped by lead for one outer lookback window."""
        if lookback_days < 1:
            return {}

        occurred_after = as_of.astimezone(UTC) - timedelta(days=lookback_days)
        event_rows = self._lead_event_repository.fetch_by_tenant_id_occurred_after(
            tenant_id=tenant_id,
            occurred_after=occurred_after,
        )

        events_by_lead_id: dict[UUID, list[PosthogLeadEvent]] = defaultdict(list)
        for event_row in event_rows:
            events_by_lead_id[event_row["lead_id"]].append(
                PosthogLeadEvent(
                    lead_id=event_row["lead_id"],
                    event_name=event_row["event_name"],
                    event_properties=dict(event_row["event_properties"]),
                    occurred_at=event_row["occurred_at"],
                )
            )
        return dict(events_by_lead_id)
