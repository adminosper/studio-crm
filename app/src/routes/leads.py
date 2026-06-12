from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from src.models.lead import LeadResponse
from src.shared.dependencies import get_lead_service
from src.shared.exceptions import LeadNotFoundError
from src.shared.http_exceptions import raise_http_exception_for_service_error
from src.shared.exceptions import TenantNotFoundError
from src.services.lead_service import LeadService

router = APIRouter(prefix="/api/core/tenants/{tenant_id}/leads", tags=["core-leads"])


@router.get("", response_model=list[LeadResponse])
def list_leads(tenant_id: UUID, lead_service: LeadService = Depends(get_lead_service)) -> list[LeadResponse]:
    """Return all leads for a tenant."""
    try:
        leads = lead_service.list_leads(tenant_id)
    except (LeadNotFoundError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return [LeadResponse.model_validate(lead) for lead in leads]


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    tenant_id: UUID,
    lead_id: UUID,
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadResponse:
    """Return one tenant-scoped lead."""
    try:
        lead = lead_service.get_lead(tenant_id, lead_id)
    except (LeadNotFoundError, TenantNotFoundError) as error:
        raise_http_exception_for_service_error(error)
    return LeadResponse.model_validate(lead)
