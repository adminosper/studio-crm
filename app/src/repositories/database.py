from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row

from src.config import Settings


def create_connection(settings: Settings) -> Connection:
    """Create a PostgreSQL connection for short-lived repository operations."""
    return Connection.connect(
        conninfo=settings.database_url,
        connect_timeout=settings.db_connect_timeout_seconds,
        row_factory=dict_row,
    )
