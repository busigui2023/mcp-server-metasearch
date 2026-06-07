"""Tests for Firecrawl Scrape tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.firecrawl_scrape import (
    FirecrawlScrapeTool,
    _format_scrape_results,
)


@pytest.fixture
def tool():
    return FirecrawlScrapeTool()


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
    """Successful scrape should return formatted content."""
    mock_data = {
        "success": True,
        "data": {
            "markdown": "# Hello World\n\nThis is test content.",
            "metadata": {
                "title": "Test Page",
                "sourceURL": "https://example.com",
                "description": "A test page",
            },
            "links": ["https://example.com/about", "https://example.com/contact"],
        },
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(url="https://example.com")

    assert "Title: Test Page" in result
    assert "URL: https://example.com" in result
    assert "Description: A test page" in result
    assert "# Hello World" in result
    assert "https://example.com/about" in result
    assert "https://example.com/contact" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["url"] == "https://example.com"
    assert payload["formats"] == ["markdown"]
    assert payload["onlyMainContent"] is True
    assert payload["timeout"] == 30000


async def test_call_with_formats(tool, mock_settings):
    """Multiple formats should be passed through."""
    mock_data = {
        "success": True,
        "data": {
            "markdown": "# MD",
            "html": "<h1>HTML</h1>",
            "metadata": {"title": "T", "sourceURL": "https://x.com"},
        },
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(
                url="https://x.com", formats=["markdown", "html", "links"]
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["formats"] == ["markdown", "html", "links"]
    assert "--- HTML ---" in result


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be included in payload."""
    mock_data = {"success": True, "data": {"markdown": "", "metadata": {}}}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            await tool.call(
                url="https://x.com",
                only_main_content=False,
                timeout=60000,
                wait_for=2000,
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["onlyMainContent"] is False
    assert payload["timeout"] == 60000
    assert payload["waitFor"] == 2000


async def test_call_invalid_format(tool, mock_settings):
    """Invalid format should raise ValueError."""
    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(ValueError, match="Unsupported format"):
            await tool.call(url="https://x.com", formats=["invalid"])


async def test_call_timeout_clamped(tool, mock_settings):
    """Timeout should be clamped to valid range."""
    mock_data = {"success": True, "data": {"markdown": "", "metadata": {}}}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)

            await tool.call(url="https://x.com", timeout=500)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["timeout"] == 1000  # clamped to min

            await tool.call(url="https://x.com", timeout=999999)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["timeout"] == 60000  # clamped to max


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch(
        "mcp_server_metasearch.tools.firecrawl_scrape.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(url="https://x.com")


def test_format_scrape_results_failed():
    """Formatter should handle failed scrape."""
    result = _format_scrape_results({"success": False, "warning": "Slow site"})
    assert "Scrape failed" in result
    assert "Slow site" in result


def test_format_scrape_results_empty():
    """Formatter should handle empty content."""
    result = _format_scrape_results({"success": True, "data": {}})
    assert "No content extracted" in result
