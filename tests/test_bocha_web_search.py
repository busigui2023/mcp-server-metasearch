"""Tests for Bocha Web Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.bocha_web_search import (
    BochaWebSearchTool,
    _format_web_search_results,
)


@pytest.fixture
def tool():
    return BochaWebSearchTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.bocha_api_key = "sk-test-key"
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
        "code": 200,
        "log_id": "log-123",
        "data": {
            "webPages": {
                "totalEstimatedMatches": 1000,
                "value": [
                    {
                        "name": "Test Result",
                        "url": "https://example.com",
                        "snippet": "This is a test snippet",
                        "summary": "AI summary here",
                        "siteName": "Example Site",
                        "siteIcon": "https://example.com/favicon.ico",
                        "datePublished": "2024-01-15",
                    }
                ],
            }
        },
    }

    with patch(
        "mcp_server_metasearch.tools.bocha_web_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test query")

    assert "搜索结果 (1" in result
    assert "约 1000 条" in result
    assert "Test Result" in result
    assert "https://example.com" in result
    assert "This is a test snippet" in result
    assert "AI summary here" in result
    assert "Example Site" in result
    assert "2024-01-15" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["query"] == "test query"
    assert payload["count"] == 5


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be included in payload."""
    mock_data = {
        "code": 200,
        "data": {"webPages": {"value": []}},
    }

    with patch(
        "mcp_server_metasearch.tools.bocha_web_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            await tool.call(
                query="test",
                count=10,
                freshness="oneWeek",
                summary=True,
                include_domains=["example.com"],
                exclude_domains=["spam.com"],
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["count"] == 10
    assert payload["freshness"] == "oneWeek"
    assert payload["summary"] is True
    assert payload["include"] == ["example.com"]
    assert payload["exclude"] == ["spam.com"]


async def test_call_count_clamped(tool, mock_settings):
    """count should be clamped to 1-50 range."""
    mock_data = {"code": 200, "data": {"webPages": {"value": []}}}

    with patch(
        "mcp_server_metasearch.tools.bocha_web_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)

            await tool.call(query="test", count=100)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["count"] == 50

            await tool.call(query="test", count=0)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["count"] == 1


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch(
        "mcp_server_metasearch.tools.bocha_web_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


async def test_call_api_error(tool, mock_settings):
    """API error response (non-200 code) should be formatted."""
    mock_data = {"code": 400, "msg": "Invalid query"}

    with patch(
        "mcp_server_metasearch.tools.bocha_web_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test")

    assert "Search failed" in result
    assert "Invalid query" in result


def test_format_web_search_results_empty():
    """Formatter should handle empty results."""
    result = _format_web_search_results({"code": 200, "data": {"webPages": {"value": []}}})
    assert "No results found" in result


def test_format_web_search_results_api_error():
    """Formatter should handle API error."""
    result = _format_web_search_results({"code": 500, "msg": "Server error"})
    assert "Search failed" in result
    assert "Server error" in result
