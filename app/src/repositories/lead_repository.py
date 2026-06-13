from __future__ import annotations

from datetime import datetime
from uuid import UUID

from psycopg import Connection


class LeadRepository:
    """Read tenant-scoped lead data from PostgreSQL."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def fetch_by_tenant_id(self, tenant_id: UUID) -> list[dict]:
        """Return all leads belonging to a tenant."""
        query = """
            SELECT
                id,
                tenant_id,
                name,
                email,
                company,
                industry,
                company_size,
                geography,
                phone,
                title,
                source,
                status,
                stage,
                score,
                score_last_updated_at,
                is_stage_manually_overridden,
                created_at,
                updated_at
            FROM leads
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at ASC
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id})
            return list(cursor.fetchall())

    def fetch_by_id(self, tenant_id: UUID, lead_id: UUID) -> dict | None:
        """Return a single lead if it exists within the tenant scope."""
        query = """
            SELECT
                id,
                tenant_id,
                name,
                email,
                company,
                industry,
                company_size,
                geography,
                phone,
                title,
                source,
                status,
                stage,
                score,
                score_last_updated_at,
                is_stage_manually_overridden,
                created_at,
                updated_at
            FROM leads
            WHERE tenant_id = %(tenant_id)s AND id = %(lead_id)s
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id, "lead_id": lead_id})
            return cursor.fetchone()

    def update_scoring_state(
        self,
        *,
        tenant_id: UUID,
        lead_id: UUID,
        score: int,
        stage: str,
        score_last_updated_at: datetime,
    ) -> None:
        """Persist one lead scoring update inside a caller-managed transaction."""
        query = """
            UPDATE leads
            SET
                score = %(score)s,
                stage = %(stage)s,
                score_last_updated_at = %(score_last_updated_at)s,
                updated_at = NOW()
            WHERE tenant_id = %(tenant_id)s AND id = %(lead_id)s
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                query,
                {
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "score": score,
                    "stage": stage,
                    "score_last_updated_at": score_last_updated_at,
                },
            )
