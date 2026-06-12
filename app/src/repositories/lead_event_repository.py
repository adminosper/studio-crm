from __future__ import annotations

from uuid import UUID

from psycopg import Connection


class LeadEventRepository:
    """Read event rows scoped to a tenant and lead."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def fetch_by_lead_id(self, tenant_id: UUID, lead_id: UUID) -> list[dict]:
        """Return all events stored for the given tenant-scoped lead."""
        query = """
            SELECT
                id,
                tenant_id,
                lead_id,
                event_name,
                event_properties,
                occurred_at,
                created_at
            FROM lead_events
            WHERE tenant_id = %(tenant_id)s AND lead_id = %(lead_id)s
            ORDER BY occurred_at DESC
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id, "lead_id": lead_id})
            return list(cursor.fetchall())
