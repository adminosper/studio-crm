from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.integrations.posthog.types import PosthogLeadEvent
from src.services.lead_scoring_engine.behavior_scorer import LeadBehaviorScorer
from src.services.lead_scoring_engine.fit_scorer import LeadFitScorer
from src.services.lead_scoring_engine.qualification import LeadQualificationService
from src.services.lead_scoring_engine.service import LeadScoringComputeService
from src.shared.exceptions import TenantNotFoundError


class _FakeTransactionContext:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    def __enter__(self) -> None:
        self._connection.transaction_entered = True
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._connection.transaction_exited = True
        return False


class _FakeConnection:
    def __init__(self) -> None:
        self.transaction_entered = False
        self.transaction_exited = False

    def transaction(self) -> _FakeTransactionContext:
        return _FakeTransactionContext(self)


class _StubTenantRepository:
    def __init__(self, tenant: dict | None) -> None:
        self._tenant = tenant

    def fetch_by_id(self, tenant_id):
        return self._tenant


class _StubLeadRepository:
    def __init__(self, leads: list[dict]) -> None:
        self._leads = leads
        self.updates: list[dict] = []

    def fetch_by_tenant_id(self, tenant_id):
        return self._leads

    def update_scoring_state(self, **kwargs) -> None:
        self.updates.append(kwargs)


class _StubLeadScoringRuleRepository:
    def __init__(self, rules: list[dict]) -> None:
        self._rules = rules

    def fetch_active_by_tenant_id(self, tenant_id):
        return self._rules


class _StubValidationService:
    def normalize_persisted_rule_config(self, *, rule_type, rule_config):
        return rule_config


class _StubPosthogService:
    def __init__(self, events_by_lead_id: dict) -> None:
        self._events_by_lead_id = events_by_lead_id

    def load_tenant_events_grouped_by_lead(self, *, tenant_id, lookback_days, as_of):
        return self._events_by_lead_id


def _build_compute_service(*, tenant: dict | None, leads: list[dict], rules: list[dict], events_by_lead_id: dict):
    connection = _FakeConnection()
    lead_repository = _StubLeadRepository(leads=leads)
    service = LeadScoringComputeService(
        connection=connection,
        tenant_repository=_StubTenantRepository(tenant=tenant),
        lead_repository=lead_repository,
        lead_scoring_rule_repository=_StubLeadScoringRuleRepository(rules=rules),
        validation_service=_StubValidationService(),
        posthog_service=_StubPosthogService(events_by_lead_id=events_by_lead_id),
        fit_scorer=LeadFitScorer(),
        behavior_scorer=LeadBehaviorScorer(),
        qualification_service=LeadQualificationService(),
    )
    return service, connection, lead_repository


def test_compute_tenant_scores_normalizes_high_score_budget_and_persists_updates():
    tenant_id = uuid4()
    lead_id = uuid4()
    tenant = {
        "id": tenant_id,
        "mql_score_threshold": 40,
        "sql_score_threshold": 70,
    }
    leads = [
        {
            "id": lead_id,
            "tenant_id": tenant_id,
            "industry": "SaaS",
            "company_size": 250,
            "geography": "US",
            "title": "Founder",
            "source": "website",
            "status": "active",
            "stage": "pre_mql",
            "score": 0,
            "is_stage_manually_overridden": False,
        },
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "industry": "SaaS",
            "company_size": 50,
            "geography": "US",
            "title": "Manager",
            "source": "manual",
            "status": "disqualified",
            "stage": "pre_mql",
            "score": 10,
            "is_stage_manually_overridden": False,
        },
    ]
    rules = [
        {
            "rule_name": "SaaS ICP",
            "rule_type": "fit",
            "score_delta": 60,
            "rule_config": {
                "field": "industry",
                "operator": "equals",
                "value": "SaaS",
            },
        },
        {
            "rule_name": "Founder Persona",
            "rule_type": "fit",
            "score_delta": 60,
            "rule_config": {
                "field": "title",
                "operator": "contains",
                "value": "Founder",
            },
        },
    ]

    service, connection, lead_repository = _build_compute_service(
        tenant=tenant,
        leads=leads,
        rules=rules,
        events_by_lead_id={},
    )

    result = service.compute_tenant_scores(tenant_id)

    assert connection.transaction_entered is True
    assert connection.transaction_exited is True
    assert result.processed_lead_count == 1
    assert result.skipped_lead_count == 1
    assert result.stage_transition_count == 1
    assert result.max_possible_score == 120
    assert result.results[0].raw_score == 120
    assert result.results[0].final_score == 100
    assert result.results[0].new_stage == "sql"
    assert result.results[1].status == "disqualified"
    assert result.results[1].matched_rule_names == []
    assert lead_repository.updates[0]["score"] == 100
    assert lead_repository.updates[0]["stage"] == "sql"


def test_compute_tenant_scores_preserves_stage_when_manual_override_is_enabled():
    tenant_id = uuid4()
    lead_id = uuid4()
    tenant = {
        "id": tenant_id,
        "mql_score_threshold": 40,
        "sql_score_threshold": 70,
    }
    leads = [
        {
            "id": lead_id,
            "tenant_id": tenant_id,
            "industry": "SaaS",
            "company_size": 250,
            "geography": "US",
            "title": "Founder",
            "source": "website",
            "status": "active",
            "stage": "pre_mql",
            "score": 0,
            "is_stage_manually_overridden": True,
        }
    ]
    rules = [
        {
            "rule_name": "Demo Request",
            "rule_type": "behavior",
            "score_delta": 80,
            "rule_config": {
                "event_name": "demo_requested",
                "aggregate_operator": "count_gte",
                "value": 1,
                "lookback_days": 30,
                "property_filters": {},
            },
        }
    ]
    as_of = datetime.now(UTC)
    events_by_lead_id = {
        lead_id: [
            PosthogLeadEvent(
                lead_id=lead_id,
                event_name="demo_requested",
                event_properties={},
                occurred_at=as_of - timedelta(days=1),
            )
        ]
    }

    service, _, lead_repository = _build_compute_service(
        tenant=tenant,
        leads=leads,
        rules=rules,
        events_by_lead_id=events_by_lead_id,
    )

    result = service.compute_tenant_scores(tenant_id)

    assert result.results[0].final_score == 80
    assert result.results[0].previous_stage == "pre_mql"
    assert result.results[0].new_stage == "pre_mql"
    assert result.stage_transition_count == 0
    assert lead_repository.updates[0]["stage"] == "pre_mql"


def test_compute_tenant_scores_keeps_score_as_is_when_tenant_score_budget_is_100_or_less():
    tenant_id = uuid4()
    lead_id = uuid4()
    tenant = {
        "id": tenant_id,
        "mql_score_threshold": 40,
        "sql_score_threshold": 70,
    }
    leads = [
        {
            "id": lead_id,
            "tenant_id": tenant_id,
            "industry": "SaaS",
            "company_size": 150,
            "geography": "US",
            "title": "Founder",
            "source": "website",
            "status": "active",
            "stage": "pre_mql",
            "score": 0,
            "is_stage_manually_overridden": False,
        }
    ]
    rules = [
        {
            "rule_name": "SaaS ICP",
            "rule_type": "fit",
            "score_delta": 30,
            "rule_config": {
                "field": "industry",
                "operator": "equals",
                "value": "SaaS",
            },
        },
        {
            "rule_name": "Founder Persona",
            "rule_type": "fit",
            "score_delta": 20,
            "rule_config": {
                "field": "title",
                "operator": "contains",
                "value": "Founder",
            },
        },
        {
            "rule_name": "Enterprise Company Size",
            "rule_type": "fit",
            "score_delta": 40,
            "rule_config": {
                "field": "company_size",
                "operator": "gte",
                "value": 500,
            },
        },
    ]

    service, _, lead_repository = _build_compute_service(
        tenant=tenant,
        leads=leads,
        rules=rules,
        events_by_lead_id={},
    )

    result = service.compute_tenant_scores(tenant_id)

    assert result.max_possible_score == 90
    assert result.results[0].raw_score == 50
    assert result.results[0].final_score == 50
    assert result.results[0].new_stage == "mql"
    assert lead_repository.updates[0]["score"] == 50


def test_compute_tenant_scores_derives_stage_from_normalized_final_score():
    tenant_id = uuid4()
    lead_id = uuid4()
    tenant = {
        "id": tenant_id,
        "mql_score_threshold": 60,
        "sql_score_threshold": 80,
    }
    leads = [
        {
            "id": lead_id,
            "tenant_id": tenant_id,
            "industry": "SaaS",
            "company_size": 250,
            "geography": "US",
            "title": "Founder",
            "source": "website",
            "status": "active",
            "stage": "pre_mql",
            "score": 0,
            "is_stage_manually_overridden": False,
        }
    ]
    rules = [
        {
            "rule_name": "SaaS ICP",
            "rule_type": "fit",
            "score_delta": 80,
            "rule_config": {
                "field": "industry",
                "operator": "equals",
                "value": "SaaS",
            },
        },
        {
            "rule_name": "Enterprise Company Size",
            "rule_type": "fit",
            "score_delta": 80,
            "rule_config": {
                "field": "company_size",
                "operator": "gte",
                "value": 500,
            },
        },
    ]

    service, _, lead_repository = _build_compute_service(
        tenant=tenant,
        leads=leads,
        rules=rules,
        events_by_lead_id={},
    )

    result = service.compute_tenant_scores(tenant_id)

    assert result.max_possible_score == 160
    assert result.results[0].raw_score == 80
    assert result.results[0].final_score == 50
    assert result.results[0].new_stage == "pre_mql"
    assert lead_repository.updates[0]["stage"] == "pre_mql"


def test_compute_tenant_scores_raises_when_tenant_is_missing():
    service, _, _ = _build_compute_service(
        tenant=None,
        leads=[],
        rules=[],
        events_by_lead_id={},
    )

    with pytest.raises(TenantNotFoundError):
        service.compute_tenant_scores(uuid4())
