from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from src.main import app
from src.services.lead_scoring_rules.contracts.service import ScoringRuleContractService
from src.shared.dependencies import get_lead_scoring_compute_service
from src.shared.dependencies import get_lead_scoring_rule_service
from src.shared.dependencies import get_lead_service
from src.shared.dependencies import get_scoring_rule_contract_service
from src.shared.dependencies import get_tenant_service
from src.shared.exceptions import LeadNotFoundError
from src.shared.exceptions import RuleConfigValidationError
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


class StubScoringComputeService:
    """Small stub for scoring compute route tests."""

    def __init__(self, result: dict | None = None, missing: Exception | None = None) -> None:
        self._result = result or {}
        self._missing = missing

    def compute_tenant_scores(self, tenant_id):
        if self._missing is not None:
            raise self._missing
        return self._result


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
        "rule_config": {"version": 1, "field": "industry", "operator": "in", "value": ["SaaS", "FinTech"]},
        "created_at": "2026-06-12T10:00:00Z",
        "updated_at": "2026-06-12T10:00:00Z",
    }


def test_list_scoring_rule_contracts_returns_versioned_contracts():
    app.dependency_overrides[get_scoring_rule_contract_service] = lambda: ScoringRuleContractService()

    with TestClient(app) as client:
        response = client.get("/api/core/scoring-rule-contracts")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert any(contract["rule_type"] == "fit" and contract["version"] == 1 for contract in response.json())
    behavior_contract = next(contract for contract in response.json() if contract["rule_type"] == "behavior")
    event_name_field = next(
        field_definition
        for field_definition in behavior_contract["field_definitions"]
        if field_definition["name"] == "event_name"
    )
    assert "pricing_page_viewed" in event_name_field["allowed_values"]


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
                    "version": 1,
                    "field": "industry",
                    "operator": "in",
                    "value": ["SaaS", "FinTech"],
                },
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["rule_name"] == "SaaS ICP"


def test_create_scoring_rule_returns_validation_error_for_invalid_contract():
    tenant_id = str(uuid4())
    validation_error = RuleConfigValidationError(
        message="unsupported rule contract version",
        field_path="rule_config.version",
        allowed_values=[1],
    )
    app.dependency_overrides[get_lead_scoring_rule_service] = (
        lambda: StubScoringRuleService(missing=validation_error)
    )

    with TestClient(app) as client:
        response = client.post(
            f"/api/core/tenants/{tenant_id}/scoring-rules",
            json={
                "rule_name": "Pricing Page Intent",
                "rule_type": "behavior",
                "score_delta": 20,
                "is_active": True,
                "rule_config": {
                    "version": 9,
                    "event_name": "pricing_page_viewed",
                    "aggregate_operator": "count_gte",
                    "value": 2,
                    "lookback_days": 30,
                },
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["field_path"] == "rule_config.version"


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


def test_compute_tenant_scores_returns_summary():
    tenant_id = str(uuid4())
    app.dependency_overrides[get_lead_scoring_compute_service] = lambda: StubScoringComputeService(
        result={
            "tenant_id": tenant_id,
            "processed_lead_count": 1,
            "skipped_lead_count": 1,
            "stage_transition_count": 1,
            "max_possible_score": 120,
            "results": [
                {
                    "lead_id": str(uuid4()),
                    "status": "active",
                    "previous_score": 0,
                    "raw_score": 120,
                    "final_score": 100,
                    "previous_stage": "pre_mql",
                    "new_stage": "sql",
                    "is_stage_manually_overridden": False,
                    "skip_reason": None,
                    "fit_score_delta": 60,
                    "behavior_score_delta": 60,
                    "matched_rule_names": ["SaaS ICP", "Demo Request"],
                }
            ],
        }
    )

    with TestClient(app) as client:
        response = client.post(f"/api/core/tenants/{tenant_id}/scoring/compute")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["processed_lead_count"] == 1
    assert response.json()["results"][0]["final_score"] == 100


def test_compute_tenant_scores_returns_not_found_when_tenant_is_missing():
    tenant_id = str(uuid4())
    app.dependency_overrides[get_lead_scoring_compute_service] = (
        lambda: StubScoringComputeService(missing=TenantNotFoundError())
    )

    with TestClient(app) as client:
        response = client.post(f"/api/core/tenants/{tenant_id}/scoring/compute")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "tenant not found"
