"""Tests for Tavily Extract tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.tavily_extract import TavilyExtractTool, _format_extract_results


@pytest.fixture
def tool():
    return TavilyExtractTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.tavily_api_key = "tvly-test-key"
    return settings


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    mock.text = str(data)
    return mock


async def test_call_single_url(tool, mock_settings):
    """Extract with a single URL string."""
    mock_response_data = {
        "results": [
            {
                "url": "https://example.com",
                "raw_content": "Hello world",
                "images": [],
            }
        ],
        "failed_results": [],
        "usage": {"credits": 1},
        "request_id": "req-456",
    }

    mock_response = _make_response(mock_response_data)

    with patch("mcp_server_metasearch.tools.tavily_extract.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await tool.call(urls="https://example.com")

    assert "https://example.com" in result
    assert "Hello world" in result
    assert "Credits used: 1" in result
    assert "Request ID: req-456" in result

    # Verify payload uses list
    payload = mock_post.call_args.kwargs["json"]
    assert payload["urls"] == ["https://example.com"]


async def test_call_multiple_urls(tool, mock_settings):
    """Extract with multiple URLs."""
    mock_response = _make_response({
        "results": [
            {"url": "https://a.com", "raw_content": "A"},
            {"url": "https://b.com", "raw_content": "B"},
        ],
        "failed_results": [],
    })

    with patch("mcp_server_metasearch.tools.tavily_extract.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await tool.call(
                urls=["https://a.com", "https://b.com"],
                query="test query",
                extract_depth="advanced",
                return_format="text",
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["urls"] == ["https://a.com", "https://b.com"]
    assert payload["query"] == "test query"
    assert payload["extract_depth"] == "advanced"
    assert payload["format"] == "text"

    assert "A" in result
    assert "B" in result


async def test_call_with_failed_results(tool, mock_settings):
    """Failed URLs should be reported separately."""
    mock_response = _make_response({
        "results": [{"url": "https://ok.com", "raw_content": "OK"}],
        "failed_results": [
            {"url": "https://fail.com", "error": "Timeout"},
        ],
    })

    with patch("mcp_server_metasearch.tools.tavily_extract.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await tool.call(urls=["https://ok.com", "https://fail.com"])

    assert "OK" in result
    assert "## Failed URLs (1)" in result
    assert "https://fail.com: Timeout" in result


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    with patch("mcp_server_metasearch.tools.tavily_extract.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(urls="https://example.com")


def test_format_extract_results_empty():
    """Formatter should handle empty response."""
    result = _format_extract_results({})
    assert result == "No extraction results."
