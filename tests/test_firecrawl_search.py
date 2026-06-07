"""Tests for Firecrawl Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.firecrawl_search import (
    FirecrawlSearchTool,
    _format_search_results,
)


@pytest.fixture
def tool():
    return FirecrawlSearchTool()


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
    """Successful search should return formatted results."""
    mock_data = {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "description": "A test result",
                }
            ],
            "images": [
                {
                    "title": "Test Image",
                    "imageUrl": "https://img.example.com/1.jpg",
                    "url": "https://example.com",
                    "imageWidth": 1920,
                    "imageHeight": 1080,
                }
            ],
            "news": [],
        },
        "creditsUsed": 4,
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test query", sources=["web", "images"])

    assert "## Web Results (1)" in result
    assert "Test Result" in result
    assert "https://example.com" in result
    assert "## Image Results (1)" in result
    assert "Test Image" in result
    assert "1920x1080" in result
    assert "Credits used: 4" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["query"] == "test query"
    assert payload["sources"] == ["web", "images"]


async def test_call_with_scrape_content(tool, mock_settings):
    """scrape_content=True should include scrapeOptions."""
    mock_data = {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "T",
                    "url": "https://x.com",
                    "markdown": "Full page content here",
                }
            ]
        },
    }

    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test", scrape_content=True)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["scrapeOptions"]["formats"] == ["markdown"]
    assert "Full page content here" in result


async def test_call_with_categories(tool, mock_settings):
    """Categories should be passed through."""
    mock_data = {"success": True, "data": {"web": []}}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            await tool.call(
                query="test",
                categories=["github", "research"],
                include_domains=["github.com"],
                exclude_domains=["spam.com"],
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["categories"] == ["github", "research"]
    assert payload["includeDomains"] == ["github.com"]
    assert payload["excludeDomains"] == ["spam.com"]


async def test_call_limit_clamped(tool, mock_settings):
    """limit should be clamped to 1-50 range."""
    mock_data = {"success": True, "data": {"web": []}}

    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)

            await tool.call(query="test", limit=100)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["limit"] == 50

            await tool.call(query="test", limit=0)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["limit"] == 1


async def test_call_invalid_source(tool, mock_settings):
    """Invalid source should raise ValueError."""
    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(ValueError, match="Unsupported source"):
            await tool.call(query="test", sources=["invalid"])


async def test_call_invalid_category(tool, mock_settings):
    """Invalid category should raise ValueError."""
    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(ValueError, match="Unsupported category"):
            await tool.call(query="test", categories=["invalid"])


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    with patch(
        "mcp_server_metasearch.tools.firecrawl_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


def test_format_search_results_empty():
    """Formatter should handle empty results."""
    result = _format_search_results({"success": True, "data": {}}, False)
    assert result == "No results found."


def test_format_search_results_failed():
    """Formatter should handle failed search."""
    result = _format_search_results(
        {"success": False, "warning": "Rate limited"}, False
    )
    assert "Search failed" in result
    assert "Rate limited" in result
