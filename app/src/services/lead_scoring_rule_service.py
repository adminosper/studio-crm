from __future__ import annotations

from uuid import UUID

from src.models.scoring_rule import ScoringRuleMutationRequest
from src.repositories.lead_scoring_rule_repository import LeadScoringRuleRepository
from src.repositories.tenant_repository import TenantRepository
from src.shared.exceptions import ScoringRuleNotFoundError
from src.shared.exceptions import TenantNotFoundError


class LeadScoringRuleService:
    """Own the tenant-scoped scoring rule CRUD workflow."""

    def __init__(
        self,
        tenant_repository: TenantRepository,
        lead_scoring_rule_repository: LeadScoringRuleRepository,
    ) -> None:
        self._tenant_repository = tenant_repository
        self._lead_scoring_rule_repository = lead_scoring_rule_repository

    def list_scoring_rules(self, tenant_id: UUID) -> list[dict]:
        """Return all scoring rules for a tenant."""
        self._require_tenant(tenant_id)
        return self._lead_scoring_rule_repository.fetch_by_tenant_id(tenant_id)

    def create_scoring_rule(self, tenant_id: UUID, payload: ScoringRuleMutationRequest) -> dict:
        """Create one scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        return self._lead_scoring_rule_repository.insert(
            tenant_id=tenant_id,
            payload=self._serialize_payload(payload),
        )

    def update_scoring_rule(self, tenant_id: UUID, rule_id: UUID, payload: ScoringRuleMutationRequest) -> dict:
        """Update one scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        updated_rule = self._lead_scoring_rule_repository.update(
            tenant_id=tenant_id,
            rule_id=rule_id,
            payload=self._serialize_payload(payload),
        )
        if updated_rule is None:
            raise ScoringRuleNotFoundError
        return updated_rule

    def delete_scoring_rule(self, tenant_id: UUID, rule_id: UUID) -> None:
        """Delete one scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        deleted = self._lead_scoring_rule_repository.delete(tenant_id=tenant_id, rule_id=rule_id)
        if not deleted:
            raise ScoringRuleNotFoundError

    def _require_tenant(self, tenant_id: UUID) -> None:
        if self._tenant_repository.fetch_by_id(tenant_id) is None:
            raise TenantNotFoundError

    def _serialize_payload(self, payload: ScoringRuleMutationRequest) -> dict:
        return {
            "rule_name": payload.rule_name,
            "rule_type": payload.rule_type,
            "score_delta": payload.score_delta,
            "is_active": payload.is_active,
            "rule_config": payload.rule_config.model_dump(),
        }
