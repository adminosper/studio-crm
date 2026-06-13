from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from src.models.scoring_rule import ScoringRuleMutationRequest
from src.models.scoring_rule import ScoringRuleResponse
from src.shared.dependencies import get_lead_scoring_rule_service
from src.shared.exceptions import RuleConfigValidationError
from src.shared.exceptions import ScoringRuleNotFoundError
from src.shared.exceptions import TenantNotFoundError
from src.shared.http_exceptions import raise_http_exception_for_service_error
from src.services.lead_scoring_rules.service import LeadScoringRuleService

router = APIRouter(prefix="/api/core/tenants/{tenant_id}/scoring-rules", tags=["core-scoring-rules"])


@router.get("", response_model=list[ScoringRuleResponse])
def list_scoring_rules(
    tenant_id: UUID,
    scoring_rule_service: LeadScoringRuleService = Depends(get_lead_scoring_rule_service),
) -> list[ScoringRuleResponse]:
    """Return all scoring rules for a tenant."""
    try:
        rules = scoring_rule_service.list_scoring_rules(tenant_id)
    except TenantNotFoundError as error:
        raise_http_exception_for_service_error(error)
    return [ScoringRuleResponse.model_validate(rule) for rule in rules]


@router.post("", response_model=ScoringRuleResponse, status_code=status.HTTP_201_CREATED)
def create_scoring_rule(
    tenant_id: UUID,
    payload: ScoringRuleMutationRequest,
    scoring_rule_service: LeadScoringRuleService = Depends(get_lead_scoring_rule_service),
) -> ScoringRuleResponse:
    """Create a tenant-scoped scoring rule."""
    try:
        rule = scoring_rule_service.create_scoring_rule(tenant_id, payload)
    except (RuleConfigValidationError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return ScoringRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=ScoringRuleResponse)
def update_scoring_rule(
    tenant_id: UUID,
    rule_id: UUID,
    payload: ScoringRuleMutationRequest,
    scoring_rule_service: LeadScoringRuleService = Depends(get_lead_scoring_rule_service),
) -> ScoringRuleResponse:
    """Update a tenant-scoped scoring rule."""
    try:
        rule = scoring_rule_service.update_scoring_rule(tenant_id, rule_id, payload)
    except (RuleConfigValidationError, ScoringRuleNotFoundError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return ScoringRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scoring_rule(
    tenant_id: UUID,
    rule_id: UUID,
    scoring_rule_service: LeadScoringRuleService = Depends(get_lead_scoring_rule_service),
) -> Response:
    """Delete a tenant-scoped scoring rule."""
    try:
        scoring_rule_service.delete_scoring_rule(tenant_id, rule_id)
    except (ScoringRuleNotFoundError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
