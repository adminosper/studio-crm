from __future__ import annotations

from uuid import UUID

from src.models.scoring_rule import ScoringRuleMutationRequest
from src.repositories.lead_scoring_rule_repository import LeadScoringRuleRepository
from src.repositories.tenant_repository import TenantRepository
from src.shared.exceptions import ScoringRuleNotFoundError
from src.shared.exceptions import TenantNotFoundError
from src.services.lead_scoring_rules.validations.service import LeadScoringRuleValidationService


class LeadScoringRuleService:
    """Own tenant-scoped scoring rule CRUD workflows."""

    def __init__(
        self,
        tenant_repository: TenantRepository,
        lead_scoring_rule_repository: LeadScoringRuleRepository,
        validation_service: LeadScoringRuleValidationService,
    ) -> None:
        self._tenant_repository = tenant_repository
        self._lead_scoring_rule_repository = lead_scoring_rule_repository
        self._validation_service = validation_service

    def list_scoring_rules(self, tenant_id: UUID) -> list[dict]:
        """Return all normalized scoring rules for a tenant."""
        self._require_tenant(tenant_id)
        raw_rules = self._lead_scoring_rule_repository.fetch_by_tenant_id(tenant_id)
        return [self._normalize_rule(rule) for rule in raw_rules]

    def create_scoring_rule(self, tenant_id: UUID, payload: ScoringRuleMutationRequest) -> dict:
        """Create one validated scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        validated_rule_config = self._validation_service.validate_and_normalize(
            rule_type=payload.rule_type,
            rule_config=payload.rule_config.model_dump(),
        )
        created_rule = self._lead_scoring_rule_repository.insert(
            tenant_id=tenant_id,
            payload=self._serialize_payload(payload=payload, rule_config=validated_rule_config),
        )
        return self._normalize_rule(created_rule)

    def update_scoring_rule(self, tenant_id: UUID, rule_id: UUID, payload: ScoringRuleMutationRequest) -> dict:
        """Update one validated scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        validated_rule_config = self._validation_service.validate_and_normalize(
            rule_type=payload.rule_type,
            rule_config=payload.rule_config.model_dump(),
        )
        updated_rule = self._lead_scoring_rule_repository.update(
            tenant_id=tenant_id,
            rule_id=rule_id,
            payload=self._serialize_payload(payload=payload, rule_config=validated_rule_config),
        )
        if updated_rule is None:
            raise ScoringRuleNotFoundError
        return self._normalize_rule(updated_rule)

    def delete_scoring_rule(self, tenant_id: UUID, rule_id: UUID) -> None:
        """Delete one scoring rule for the tenant."""
        self._require_tenant(tenant_id)
        deleted = self._lead_scoring_rule_repository.delete(tenant_id=tenant_id, rule_id=rule_id)
        if not deleted:
            raise ScoringRuleNotFoundError

    def _normalize_rule(self, rule: dict) -> dict:
        normalized_rule = dict(rule)
        normalized_rule["rule_config"] = self._validation_service.normalize_persisted_rule_config(
            rule_type=normalized_rule["rule_type"],
            rule_config=normalized_rule["rule_config"],
        )
        return normalized_rule

    def _require_tenant(self, tenant_id: UUID) -> None:
        if self._tenant_repository.fetch_by_id(tenant_id) is None:
            raise TenantNotFoundError

    def _serialize_payload(self, payload: ScoringRuleMutationRequest, rule_config: dict) -> dict:
        return {
            "rule_name": payload.rule_name,
            "rule_type": payload.rule_type,
            "score_delta": payload.score_delta,
            "is_active": payload.is_active,
            "rule_config": rule_config,
        }
