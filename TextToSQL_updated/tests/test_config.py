"""Tests for configuration"""

import os
import pytest
from src.config import Settings


def test_settings_from_env():
    """Test loading settings from environment"""
    os.environ["DB_USER"] = "testuser"
    os.environ["DB_PASSWORD"] = "testpass"
    os.environ["DB_HOST"] = "testhost"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_NAME"] = "testdb"
    os.environ["LLM_MODEL"] = "test-model"
    os.environ["GOOGLE_API_KEY"] = "test-key"

    settings = Settings.from_env()

    assert settings.database.user == "testuser"
    assert settings.database.password == "testpass"
    assert settings.database.host == "testhost"
    assert settings.database.port == 5432
    assert settings.database.db_name == "testdb"
    assert settings.llm.model == "test-model"
    assert settings.llm.api_key == "test-key"


def test_database_uri():
    """Test database URI generation"""
    from src.config.settings import DatabaseConfig

    db_config = DatabaseConfig(
        user="user",
        password="pass",
        host="localhost",
        port=3306,
        db_name="testdb",
    )

    expected_uri = "mysql+pymysql://user:pass@localhost:3306/testdb"
    assert db_config.uri == expected_uri
