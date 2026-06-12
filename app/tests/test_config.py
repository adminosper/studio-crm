from __future__ import annotations

from src.config import Settings


def test_settings_use_default_values_when_env_is_missing():
    settings = Settings(_env_file=None)

    assert settings.app_name == "Meraki Lead Scoring API"
    assert settings.postgres_db == "meraki_lead_scoring"
    assert settings.app_port == 8000


def test_database_url_is_composed_from_settings_fields():
    settings = Settings(
        _env_file=None,
        app_name="ignored custom name",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5433,
        POSTGRES_DB="lead_scoring",
        POSTGRES_USER="user1",
        POSTGRES_PASSWORD="secret1",
    )

    assert settings.app_name == "ignored custom name"
    assert settings.database_url == "postgresql://user1:secret1@db:5433/lead_scoring"
