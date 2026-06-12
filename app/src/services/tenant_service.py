from __future__ import annotations

from uuid import UUID

from src.models.tenant import TenantScoringThresholdsUpdateRequest
from src.repositories.tenant_repository import TenantRepository
from src.shared.exceptions import TenantNotFoundError


class TenantService:
    """Own tenant-scoped scoring threshold configuration workflows."""

    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenant_repository = tenant_repository

    def get_scoring_thresholds(self, tenant_id: UUID) -> dict:
        """Return the current thresholds for a tenant."""
        tenant = self._tenant_repository.fetch_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError
        return tenant

    def update_scoring_thresholds(self, tenant_id: UUID, payload: TenantScoringThresholdsUpdateRequest) -> dict:
        """Update and return a tenant's thresholds."""
        tenant = self._tenant_repository.update_thresholds(
            tenant_id=tenant_id,
            mql_score_threshold=payload.mql_score_threshold,
            sql_score_threshold=payload.sql_score_threshold,
        )
        if tenant is None:
            raise TenantNotFoundError
        return tenant
