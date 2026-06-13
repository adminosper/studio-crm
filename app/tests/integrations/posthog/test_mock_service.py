from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.integrations.posthog.mock_service import MockPosthogService


class _StubLeadEventRepository:
    def __init__(self, event_rows: list[dict]) -> None:
        self._event_rows = event_rows
        self.calls: list[dict] = []

    def fetch_by_tenant_id_occurred_after(self, tenant_id, occurred_after):
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "occurred_after": occurred_after,
            }
        )
        return self._event_rows


def test_load_tenant_events_grouped_by_lead_groups_rows_and_converts_to_domain_events():
    tenant_id = uuid4()
    first_lead_id = uuid4()
    second_lead_id = uuid4()
    as_of = datetime(2026, 6, 13, 10, 0, tzinfo=UTC)
    repository = _StubLeadEventRepository(
        event_rows=[
            {
                "lead_id": first_lead_id,
                "event_name": "pricing_page_viewed",
                "event_properties": {"page": "pricing"},
                "occurred_at": as_of - timedelta(days=1),
            },
            {
                "lead_id": first_lead_id,
                "event_name": "demo_requested",
                "event_properties": {"channel": "website"},
                "occurred_at": as_of - timedelta(days=2),
            },
            {
                "lead_id": second_lead_id,
                "event_name": "case_study_downloaded",
                "event_properties": {"asset": "fraud-detection"},
                "occurred_at": as_of - timedelta(days=3),
            },
        ]
    )

    service = MockPosthogService(lead_event_repository=repository)

    grouped_events = service.load_tenant_events_grouped_by_lead(
        tenant_id=tenant_id,
        lookback_days=30,
        as_of=as_of,
    )

    assert repository.calls[0]["tenant_id"] == tenant_id
    assert repository.calls[0]["occurred_after"] == as_of - timedelta(days=30)
    assert len(grouped_events[first_lead_id]) == 2
    assert grouped_events[first_lead_id][0].event_name == "pricing_page_viewed"
    assert grouped_events[second_lead_id][0].event_properties == {"asset": "fraud-detection"}


def test_load_tenant_events_grouped_by_lead_returns_empty_without_query_when_lookback_is_zero():
    repository = _StubLeadEventRepository(event_rows=[])
    service = MockPosthogService(lead_event_repository=repository)

    grouped_events = service.load_tenant_events_grouped_by_lead(
        tenant_id=uuid4(),
        lookback_days=0,
        as_of=datetime(2026, 6, 13, 10, 0, tzinfo=UTC),
    )

    assert grouped_events == {}
    assert repository.calls == []
