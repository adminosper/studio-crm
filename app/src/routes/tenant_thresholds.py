from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.models.tenant import TenantScoringThresholdsResponse
from src.models.tenant import TenantScoringThresholdsUpdateRequest
from src.shared.dependencies import get_tenant_service
from src.shared.exceptions import TenantNotFoundError
from src.shared.http_exceptions import raise_http_exception_for_service_error
from src.services.tenant_service import TenantService

router = APIRouter(
    prefix="/api/core/tenants/{tenant_id}/scoring-thresholds",
    tags=["core-tenant-thresholds"],
)


@router.get("", response_model=TenantScoringThresholdsResponse)
def get_scoring_thresholds(
    tenant_id: UUID,
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantScoringThresholdsResponse:
    """Return the current scoring thresholds for a tenant."""
    try:
        tenant = tenant_service.get_scoring_thresholds(tenant_id)
    except TenantNotFoundError as error:
        raise_http_exception_for_service_error(error)
    return TenantScoringThresholdsResponse.model_validate(tenant)


@router.put("", response_model=TenantScoringThresholdsResponse)
def update_scoring_thresholds(
    tenant_id: UUID,
    payload: TenantScoringThresholdsUpdateRequest,
    tenant_service: TenantService = Depends(get_tenant_service),
) -> TenantScoringThresholdsResponse:
    """Update the scoring thresholds for a tenant."""
    try:
        tenant = tenant_service.update_scoring_thresholds(tenant_id, payload)
    except TenantNotFoundError as error:
        raise_http_exception_for_service_error(error)
    return TenantScoringThresholdsResponse.model_validate(tenant)
