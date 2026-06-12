from __future__ import annotations

from uuid import UUID

from psycopg import Connection


class TenantRepository:
    """Read and update tenant-scoped configuration state."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def fetch_by_id(self, tenant_id: UUID) -> dict | None:
        """Return one tenant if it exists and is not soft-deleted."""
        query = """
            SELECT
                id,
                name,
                mql_score_threshold,
                sql_score_threshold,
                created_at,
                deleted_at
            FROM tenants
            WHERE id = %(tenant_id)s AND deleted_at IS NULL
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id})
            return cursor.fetchone()

    def update_thresholds(self, tenant_id: UUID, mql_score_threshold: int, sql_score_threshold: int) -> dict | None:
        """Update a tenant's scoring thresholds if the tenant exists."""
        query = """
            UPDATE tenants
            SET
                mql_score_threshold = %(mql_score_threshold)s,
                sql_score_threshold = %(sql_score_threshold)s
            WHERE id = %(tenant_id)s AND deleted_at IS NULL
            RETURNING
                id,
                name,
                mql_score_threshold,
                sql_score_threshold,
                created_at,
                deleted_at
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                query,
                {
                    "tenant_id": tenant_id,
                    "mql_score_threshold": mql_score_threshold,
                    "sql_score_threshold": sql_score_threshold,
                },
            )
            updated_tenant = cursor.fetchone()
        self._connection.commit()
        return updated_tenant
