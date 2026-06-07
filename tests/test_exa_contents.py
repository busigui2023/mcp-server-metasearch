"""Tests for Exa Contents tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.exa_contents import ExaContentsTool, _format_contents_results


@pytest.fixture
def tool():
    return ExaContentsTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.exa_api_key = "exa-test-key"
    return settings


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    mock.text = str(data)
    return mock


async def test_call_single_url(tool, mock_settings):
    """Extract with a single URL string."""
    mock_data = {
        "requestId": "req-111",
        "results": [
            {
                "title": "Example Page",
                "url": "https://example.com",
                "text": "Hello world",
            }
        ],
        "statuses": [{"id": "https://example.com", "status": "success"}],
        "costDollars": {"total": 0.003},
    }

    with patch("mcp_server_metasearch.tools.exa_contents.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(urls="https://example.com")

    assert "Example Page" in result
    assert "Hello world" in result
    assert "Cost: $0.003" in result

    # Verify payload uses list and top-level text
    payload = mock_post.call_args.kwargs["json"]
    assert payload["urls"] == ["https://example.com"]
    assert payload["text"] is True


async def test_call_multiple_urls(tool, mock_settings):
    """Extract with multiple URLs and subpages."""
    mock_data = {
        "requestId": "req-222",
        "results": [
            {"title": "A", "url": "https://a.com", "text": "Content A"},
            {"title": "B", "url": "https://b.com", "text": "Content B"},
        ],
        "statuses": [
            {"id": "https://a.com", "status": "success"},
            {"id": "https://b.com", "status": "success"},
        ],
    }

    with patch("mcp_server_metasearch.tools.exa_contents.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(
                urls=["https://a.com", "https://b.com"],
                content_mode="highlights",
                max_age_hours=24,
                subpages=5,
                subpage_target=["docs", "api"],
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["urls"] == ["https://a.com", "https://b.com"]
    assert payload["highlights"] is True
    assert payload["maxAgeHours"] == 24
    assert payload["subpages"] == 5
    assert payload["subpageTarget"] == ["docs", "api"]

    assert "Content A" in result
    assert "Content B" in result


async def test_call_with_failed_statuses(tool, mock_settings):
    """Per-URL failures should be reported from statuses array."""
    mock_data = {
        "requestId": "req-333",
        "results": [{"title": "OK", "url": "https://ok.com", "text": "OK"}],
        "statuses": [
            {"id": "https://ok.com", "status": "success"},
            {"id": "https://fail.com", "status": "error", "error": {"tag": "CRAWL_TIMEOUT"}},
        ],
    }

    with patch("mcp_server_metasearch.tools.exa_contents.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(urls=["https://ok.com", "https://fail.com"])

    assert "OK" in result
    assert "## Failed URLs (1)" in result
    assert "https://fail.com: CRAWL_TIMEOUT" in result


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    with patch("mcp_server_metasearch.tools.exa_contents.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(urls="https://example.com")


def test_format_contents_results_empty():
    """Formatter should handle empty response."""
    result = _format_contents_results({})
    assert result == "No extraction results."
