from __future__ import annotations

from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb


class LeadScoringRuleRepository:
    """Manage tenant-scoped scoring rule records."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def fetch_by_tenant_id(self, tenant_id: UUID) -> list[dict]:
        """Return all scoring rules for a tenant."""
        query = """
            SELECT
                id,
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config,
                created_at,
                updated_at
            FROM lead_scoring_rules
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at ASC
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id})
            return list(cursor.fetchall())

    def fetch_active_by_tenant_id(self, tenant_id: UUID) -> list[dict]:
        """Return only active scoring rules for a tenant."""
        query = """
            SELECT
                id,
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config,
                created_at,
                updated_at
            FROM lead_scoring_rules
            WHERE tenant_id = %(tenant_id)s AND is_active = TRUE
            ORDER BY created_at ASC
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id})
            return list(cursor.fetchall())

    def fetch_by_id(self, tenant_id: UUID, rule_id: UUID) -> dict | None:
        """Return one scoring rule if it exists within the tenant scope."""
        query = """
            SELECT
                id,
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config,
                created_at,
                updated_at
            FROM lead_scoring_rules
            WHERE tenant_id = %(tenant_id)s AND id = %(rule_id)s
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id, "rule_id": rule_id})
            return cursor.fetchone()

    def insert(self, tenant_id: UUID, payload: dict) -> dict:
        """Insert and return a new scoring rule for a tenant."""
        query = """
            INSERT INTO lead_scoring_rules (
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config
            )
            VALUES (
                %(tenant_id)s,
                %(rule_name)s,
                %(rule_type)s,
                %(score_delta)s,
                %(is_active)s,
                %(rule_config)s::jsonb
            )
            RETURNING
                id,
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config,
                created_at,
                updated_at
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                query,
                {
                    "tenant_id": tenant_id,
                    "rule_name": payload["rule_name"],
                    "rule_type": payload["rule_type"],
                    "score_delta": payload["score_delta"],
                    "is_active": payload["is_active"],
                    "rule_config": Jsonb(payload["rule_config"]),
                },
            )
            created_rule = cursor.fetchone()
        self._connection.commit()
        return created_rule

    def update(self, tenant_id: UUID, rule_id: UUID, payload: dict) -> dict | None:
        """Update and return a tenant-scoped scoring rule."""
        query = """
            UPDATE lead_scoring_rules
            SET
                rule_name = %(rule_name)s,
                rule_type = %(rule_type)s,
                score_delta = %(score_delta)s,
                is_active = %(is_active)s,
                rule_config = %(rule_config)s::jsonb,
                updated_at = NOW()
            WHERE tenant_id = %(tenant_id)s AND id = %(rule_id)s
            RETURNING
                id,
                tenant_id,
                rule_name,
                rule_type,
                score_delta,
                is_active,
                rule_config,
                created_at,
                updated_at
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                query,
                {
                    "tenant_id": tenant_id,
                    "rule_id": rule_id,
                    "rule_name": payload["rule_name"],
                    "rule_type": payload["rule_type"],
                    "score_delta": payload["score_delta"],
                    "is_active": payload["is_active"],
                    "rule_config": Jsonb(payload["rule_config"]),
                },
            )
            updated_rule = cursor.fetchone()
        self._connection.commit()
        return updated_rule

    def delete(self, tenant_id: UUID, rule_id: UUID) -> bool:
        """Delete a scoring rule if it exists within the tenant scope."""
        query = """
            DELETE FROM lead_scoring_rules
            WHERE tenant_id = %(tenant_id)s AND id = %(rule_id)s
        """
        with self._connection.cursor() as cursor:
            cursor.execute(query, {"tenant_id": tenant_id, "rule_id": rule_id})
            deleted = cursor.rowcount == 1
        self._connection.commit()
        return deleted
