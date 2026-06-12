from __future__ import annotations

from uuid import UUID

from src.repositories.lead_repository import LeadRepository
from src.repositories.tenant_repository import TenantRepository
from src.shared.exceptions import LeadNotFoundError
from src.shared.exceptions import TenantNotFoundError


class LeadService:
    """Own tenant-scoped lead read workflows."""

    def __init__(self, tenant_repository: TenantRepository, lead_repository: LeadRepository) -> None:
        self._tenant_repository = tenant_repository
        self._lead_repository = lead_repository

    def list_leads(self, tenant_id: UUID) -> list[dict]:
        """Return all leads for a tenant."""
        self._require_tenant(tenant_id)
        return self._lead_repository.fetch_by_tenant_id(tenant_id)

    def get_lead(self, tenant_id: UUID, lead_id: UUID) -> dict:
        """Return one lead for a tenant or raise if not found."""
        self._require_tenant(tenant_id)
        lead = self._lead_repository.fetch_by_id(tenant_id, lead_id)
        if lead is None:
            raise LeadNotFoundError
        return lead

    def _require_tenant(self, tenant_id: UUID) -> None:
        if self._tenant_repository.fetch_by_id(tenant_id) is None:
            raise TenantNotFoundError
