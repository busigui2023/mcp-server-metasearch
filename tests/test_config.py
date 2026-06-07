"""Tests for configuration module."""


import pytest

from mcp_server_metasearch.config import get_settings


@pytest.fixture
def settings(monkeypatch):
    """Provide a fresh Settings instance for each test."""
    monkeypatch.delenv("TOOL_TEST_SWITCH_ENABLED", raising=False)
    return get_settings()


def test_settings_instance_exists(settings):
    """Verify settings instance can be created."""
    assert settings is not None


def test_tool_switch_disabled_by_default(settings):
    """Tool switches should default to False when env var is absent."""
    result = settings.is_tool_enabled("TOOL_NONEXISTENT_ENABLED")
    assert result is False


def test_tool_switch_true_values(settings, monkeypatch):
    """Tool switches should accept various truthy representations."""
    for value in ("true", "True", "TRUE", "1", "yes", "on"):
        monkeypatch.setenv("TOOL_TEST_SWITCH_ENABLED", value)
        assert settings.is_tool_enabled("TOOL_TEST_SWITCH_ENABLED") is True

    monkeypatch.delenv("TOOL_TEST_SWITCH_ENABLED")
