from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from psycopg import Connection
from psycopg.rows import dict_row

from src.config import Settings
from src.config import get_settings


def create_connection(settings: Settings) -> Connection:
    """Create a PostgreSQL connection for the current application settings."""
    return Connection.connect(
        conninfo=settings.database_url,
        connect_timeout=settings.db_connect_timeout_seconds,
        row_factory=dict_row,
    )


def get_db_connection(settings: Settings = Depends(get_settings)) -> Generator[Connection, None, None]:
    """Yield one database connection for the current request lifecycle."""
    with create_connection(settings) as connection:
        yield connection
