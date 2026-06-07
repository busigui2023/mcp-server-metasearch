"""Tests for tool registry module."""

from unittest.mock import MagicMock, patch

from mcp.server.fastmcp import FastMCP

from mcp_server_metasearch.tool_registry import discover_tools, register_tools
from mcp_server_metasearch.tools.base import BaseTool


class MockTool(BaseTool):
    """A mock tool for testing."""

    name = "mock_tool"
    description = "A mock tool for testing."
    required_env_vars = []
    enabled_env_var = "TOOL_MOCK_ENABLED"

    async def call(self) -> str:
        return "mock result"


class MockToolWithKey(BaseTool):
    """A mock tool that requires an API key."""

    name = "mock_tool_with_key"
    description = "A mock tool requiring an API key."
    required_env_vars = ["MOCK_API_KEY"]
    enabled_env_var = "TOOL_MOCK_WITH_KEY_ENABLED"

    async def call(self) -> str:
        return "mock result with key"


def test_discover_tools_finds_jina_tools():
    """Discovery should find all built-in jina tools."""
    tools = discover_tools()
    names = [t.name for t in tools]
    assert "jina_reader" in names
    assert "jina_search" in names
    assert "jina_deepsearch" in names


def test_discover_tools_finds_tavily_tools():
    """Discovery should find all built-in tavily tools."""
    tools = discover_tools()
    names = [t.name for t in tools]
    assert "tavily_search" in names
    assert "tavily_extract" in names
    assert "tavily_research" in names


def test_discover_tools_finds_exa_tools():
    """Discovery should find all built-in exa tools."""
    tools = discover_tools()
    names = [t.name for t in tools]
    assert "exa_search" in names
    assert "exa_contents" in names
    assert "exa_answer" in names


def test_register_tools_success(monkeypatch):
    """Tools with switch ON and no key requirement should register."""
    monkeypatch.setenv("TOOL_MOCK_ENABLED", "true")

    mock_settings = MagicMock()
    mock_settings.is_tool_enabled.return_value = True
    mock_settings.has_api_key.return_value = True

    with patch("mcp_server_metasearch.config.get_settings", return_value=mock_settings):
        mcp = FastMCP("test")
        # Temporarily inject mock tool into tools/ directory for discovery
        # Since discover_tools scans filesystem, we test via a simpler path:
        # directly call register_tools with mocked discover_tools
        with patch(
            "mcp_server_metasearch.tool_registry.discover_tools",
            return_value=[MockTool()],
        ):
            registered, diagnostics = register_tools(mcp)

    assert len(registered) == 1
    assert registered[0].name == "mock_tool"
    assert diagnostics[0].result == "Registered"


def test_register_tools_switch_disabled(monkeypatch):
    """Tools with switch OFF should be skipped."""
    mock_settings = MagicMock()
    mock_settings.is_tool_enabled.return_value = False
    mock_settings.has_api_key.return_value = True

    with patch("mcp_server_metasearch.config.get_settings", return_value=mock_settings):
        with patch(
            "mcp_server_metasearch.tool_registry.discover_tools",
            return_value=[MockTool()],
        ):
            registered, diagnostics = register_tools(FastMCP("test"))

    assert len(registered) == 0
    assert diagnostics[0].result == "Skipped (switch disabled)"


def test_register_tools_missing_key(monkeypatch):
    """Tools with missing API key should be skipped."""
    mock_settings = MagicMock()
    mock_settings.is_tool_enabled.return_value = True
    mock_settings.has_api_key.return_value = False

    with patch("mcp_server_metasearch.config.get_settings", return_value=mock_settings):
        with patch(
            "mcp_server_metasearch.tool_registry.discover_tools",
            return_value=[MockToolWithKey()],
        ):
            registered, diagnostics = register_tools(FastMCP("test"))

    assert len(registered) == 0
    assert diagnostics[0].result == "Skipped (missing API key)"


def test_register_tools_duplicate_name(monkeypatch):
    """Duplicate tool names should be skipped."""
    mock_settings = MagicMock()
    mock_settings.is_tool_enabled.return_value = True
    mock_settings.has_api_key.return_value = True

    with patch("mcp_server_metasearch.config.get_settings", return_value=mock_settings):
        with patch(
            "mcp_server_metasearch.tool_registry.discover_tools",
            return_value=[MockTool(), MockTool()],
        ):
            registered, diagnostics = register_tools(FastMCP("test"))

    assert len(registered) == 1
    assert diagnostics[1].result == "Skipped (duplicate name)"
