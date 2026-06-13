from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.models.scoring_compute import ScoringComputeResponse
from src.shared.dependencies import get_lead_scoring_compute_service
from src.shared.exceptions import RuleConfigValidationError
from src.shared.exceptions import TenantNotFoundError
from src.shared.http_exceptions import raise_http_exception_for_service_error
from src.services.lead_scoring_engine.service import LeadScoringComputeService

router = APIRouter(prefix="/api/core/tenants/{tenant_id}/scoring", tags=["core-scoring-compute"])


@router.post("/compute", response_model=ScoringComputeResponse)
def compute_tenant_scores(
    tenant_id: UUID,
    scoring_compute_service: LeadScoringComputeService = Depends(get_lead_scoring_compute_service),
) -> ScoringComputeResponse:
    """Compute and persist lead scores for one tenant."""
    try:
        computation_summary = scoring_compute_service.compute_tenant_scores(tenant_id)
    except (RuleConfigValidationError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return ScoringComputeResponse.model_validate(computation_summary)
