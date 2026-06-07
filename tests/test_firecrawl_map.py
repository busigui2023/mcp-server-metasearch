"""Tests for Firecrawl Map tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.firecrawl_map import (
    FirecrawlMapTool,
    _format_map_results,
)


@pytest.fixture
def tool():
    return FirecrawlMapTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.firecrawl_api_key = "fc-test-key"
    return settings


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    mock.text = str(data)
    return mock


async def test_call_success(tool, mock_settings):
    """Successful map should return formatted URL list."""
    mock_data = {
        "success": True,
        "links": [
            {
                "url": "https://docs.example.com/intro",
                "title": "Introduction",
                "description": "Getting started guide",
            },
            {
                "url": "https://docs.example.com/api",
                "title": "API Reference",
                "description": "API documentation",
            },
        ],
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(url="https://docs.example.com")

    assert "Found 2 URLs" in result
    assert "Introduction" in result
    assert "https://docs.example.com/intro" in result
    assert "Getting started guide" in result
    assert "API Reference" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["url"] == "https://docs.example.com"
    assert payload["limit"] == 100


async def test_call_with_search(tool, mock_settings):
    """Search parameter should filter URLs."""
    mock_data = {
        "success": True,
        "links": [
            {"url": "https://docs.example.com/api", "title": "API"},
        ],
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(
                url="https://docs.example.com", search="api", limit=50
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["search"] == "api"
    assert payload["limit"] == 50
    assert "API" in result


async def test_call_with_string_links(tool, mock_settings):
    """Map should handle string-only links."""
    mock_data = {
        "success": True,
        "links": [
            "https://example.com/page1",
            "https://example.com/page2",
        ],
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(url="https://example.com")

    assert "https://example.com/page1" in result
    assert "https://example.com/page2" in result


async def test_call_limit_clamped(tool, mock_settings):
    """limit should be clamped to valid range."""
    mock_data = {"success": True, "links": []}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)

            await tool.call(url="https://x.com", limit=0)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["limit"] == 1

            await tool.call(url="https://x.com", limit=99999)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["limit"] == 10000


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(url="https://x.com")


async def test_call_empty_links(tool, mock_settings):
    """Empty links should be handled gracefully."""
    mock_data = {"success": True, "links": []}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_map.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(url="https://empty.com")

    assert "No URLs found" in result


def test_format_map_results_empty():
    """Formatter should handle empty data."""
    result = _format_map_results({"success": False}, "https://x.com")
    assert "Map failed" in result
