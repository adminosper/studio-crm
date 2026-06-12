from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from src.main import app
from src.shared.dependencies import get_lead_scoring_rule_service
from src.shared.dependencies import get_lead_service
from src.shared.dependencies import get_tenant_service
from src.shared.exceptions import LeadNotFoundError
from src.shared.exceptions import ScoringRuleNotFoundError
from src.shared.exceptions import TenantNotFoundError


class StubTenantService:
    """Small stub for tenant threshold endpoint tests."""

    def __init__(self, tenant: dict | None = None, missing: bool = False) -> None:
        self._tenant = tenant or {}
        self._missing = missing

    def get_scoring_thresholds(self, tenant_id):
        if self._missing:
            raise TenantNotFoundError
        return self._tenant

    def update_scoring_thresholds(self, tenant_id, payload):
        if self._missing:
            raise TenantNotFoundError
        return {
            **self._tenant,
            "mql_score_threshold": payload.mql_score_threshold,
            "sql_score_threshold": payload.sql_score_threshold,
        }


class StubLeadService:
    """Small stub for lead route tests."""

    def __init__(self, leads: list[dict] | None = None, lead: dict | None = None, missing: Exception | None = None) -> None:
        self._leads = leads or []
        self._lead = lead or {}
        self._missing = missing

    def list_leads(self, tenant_id):
        if self._missing is not None:
            raise self._missing
        return self._leads

    def get_lead(self, tenant_id, lead_id):
        if self._missing is not None:
            raise self._missing
        return self._lead


class StubScoringRuleService:
    """Small stub for scoring rule route tests."""

    def __init__(self, rules=None, rule=None, missing: Exception | None = None) -> None:
        self._rules = rules or []
        self._rule = rule or {}
        self._missing = missing

    def list_scoring_rules(self, tenant_id):
        if self._missing is not None:
            raise self._missing
        return self._rules

    def create_scoring_rule(self, tenant_id, payload):
        if self._missing is not None:
            raise self._missing
        return self._rule

    def update_scoring_rule(self, tenant_id, rule_id, payload):
        if self._missing is not None:
            raise self._missing
        return self._rule

    def delete_scoring_rule(self, tenant_id, rule_id):
        if self._missing is not None:
            raise self._missing
        return None


def _sample_tenant() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Acme SaaS",
        "mql_score_threshold": 40,
        "sql_score_threshold": 70,
        "created_at": "2026-06-12T10:00:00Z",
        "deleted_at": None,
    }


def _sample_lead() -> dict:
    tenant_id = uuid4()
    return {
        "id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "name": "Alice Carter",
        "email": "alice@example.com",
        "company": "Northwind",
        "industry": "SaaS",
        "company_size": 320,
        "geography": "US",
        "phone": "+1-555-0101",
        "title": "Founder",
        "source": "manual",
        "status": "active",
        "stage": "pre_mql",
        "score": 0,
        "score_last_updated_at": None,
        "is_stage_manually_overridden": False,
        "created_at": "2026-06-12T10:00:00Z",
        "updated_at": "2026-06-12T10:00:00Z",
    }


def _sample_rule() -> dict:
    return {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "rule_name": "SaaS ICP",
        "rule_type": "fit",
        "score_delta": 20,
        "is_active": True,
        "rule_config": {"field": "industry", "operator": "in", "value": ["SaaS", "FinTech"]},
        "created_at": "2026-06-12T10:00:00Z",
        "updated_at": "2026-06-12T10:00:00Z",
    }


def test_get_scoring_thresholds_returns_tenant_configuration():
    tenant = _sample_tenant()
    app.dependency_overrides[get_tenant_service] = lambda: StubTenantService(tenant=tenant)

    with TestClient(app) as client:
        response = client.get(f"/api/core/tenants/{tenant['id']}/scoring-thresholds")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["name"] == "Acme SaaS"


def test_list_leads_returns_tenant_scoped_leads():
    tenant_id = str(uuid4())
    lead = _sample_lead() | {"tenant_id": tenant_id}
    app.dependency_overrides[get_lead_service] = lambda: StubLeadService(leads=[lead])

    with TestClient(app) as client:
        response = client.get(f"/api/core/tenants/{tenant_id}/leads")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["email"] == "alice@example.com"


def test_get_lead_returns_not_found_when_service_raises():
    tenant_id = str(uuid4())
    lead_id = str(uuid4())
    app.dependency_overrides[get_lead_service] = lambda: StubLeadService(missing=LeadNotFoundError())

    with TestClient(app) as client:
        response = client.get(f"/api/core/tenants/{tenant_id}/leads/{lead_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "lead not found"


def test_create_scoring_rule_returns_created_rule():
    tenant_id = str(uuid4())
    rule = _sample_rule() | {"tenant_id": tenant_id}
    app.dependency_overrides[get_lead_scoring_rule_service] = lambda: StubScoringRuleService(rule=rule)

    with TestClient(app) as client:
        response = client.post(
            f"/api/core/tenants/{tenant_id}/scoring-rules",
            json={
                "rule_name": "SaaS ICP",
                "rule_type": "fit",
                "score_delta": 20,
                "is_active": True,
                "rule_config": {
                    "field": "industry",
                    "operator": "in",
                    "value": ["SaaS", "FinTech"],
                },
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["rule_name"] == "SaaS ICP"


def test_delete_scoring_rule_returns_not_found_when_service_raises():
    tenant_id = str(uuid4())
    rule_id = str(uuid4())
    app.dependency_overrides[get_lead_scoring_rule_service] = (
        lambda: StubScoringRuleService(missing=ScoringRuleNotFoundError())
    )

    with TestClient(app) as client:
        response = client.delete(f"/api/core/tenants/{tenant_id}/scoring-rules/{rule_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "scoring rule not found"
