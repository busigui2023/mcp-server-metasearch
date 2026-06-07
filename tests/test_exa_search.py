"""Tests for Exa Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.exa_search import ExaSearchTool, _format_search_results


@pytest.fixture
def tool():
    return ExaSearchTool()


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


async def test_call_success(tool, mock_settings):
    """Successful search should return formatted results."""
    mock_data = {
        "requestId": "req-123",
        "searchType": "auto",
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "author": "John Doe",
                "publishedDate": "2024-01-15",
                "highlights": ["Key excerpt 1", "Key excerpt 2"],
            }
        ],
        "costDollars": {"total": 0.007},
    }

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test query")

    assert "Search Type: auto" in result
    assert "Request ID: req-123" in result
    assert "Test Result" in result
    assert "https://example.com" in result
    assert "John Doe" in result
    assert "Key excerpt 1" in result
    assert "Key excerpt 2" in result
    assert "Cost: $0.007" in result


async def test_call_with_text_mode(tool, mock_settings):
    """Text content mode should request full page text."""
    mock_data = {
        "requestId": "req-456",
        "results": [{"title": "T", "url": "https://x.com", "text": "Full text here"}],
    }

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test", content_mode="text")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["contents"]["text"] is True
    assert "highlights" not in payload.get("contents", {})
    assert "Full text here" in result


async def test_call_with_summary_mode(tool, mock_settings):
    """Summary content mode should request LLM summary."""
    mock_data = {
        "requestId": "req-789",
        "results": [{"title": "T", "url": "https://x.com", "summary": "A summary"}],
    }

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test", content_mode="summary")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["contents"]["summary"] is True
    assert "A summary" in result


async def test_call_with_optional_params(tool, mock_settings):
    """Optional parameters should be included in the payload."""
    mock_data = {"requestId": "req", "results": []}

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            await tool.call(
                query="test",
                type="deep",
                num_results=5,
                category="news",
                include_domains=["nytimes.com"],
                exclude_domains=["spam.com"],
                max_age_hours=24,
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["type"] == "deep"
    assert payload["numResults"] == 5
    assert payload["category"] == "news"
    assert payload["includeDomains"] == ["nytimes.com"]
    assert payload["excludeDomains"] == ["spam.com"]
    assert payload["contents"]["maxAgeHours"] == 24


async def test_call_num_results_clamped(tool, mock_settings):
    """num_results should be clamped to 1-100 range."""
    mock_data = {"requestId": "req", "results": []}

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)

            await tool.call(query="test", num_results=200)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["numResults"] == 100

            await tool.call(query="test", num_results=0)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["numResults"] == 1


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


async def test_call_with_output(tool, mock_settings):
    """Deep search with synthesized output should be formatted."""
    mock_data = {
        "requestId": "req-deep",
        "results": [{"title": "R1", "url": "https://x.com"}],
        "output": {
            "content": "Synthesized answer here",
            "grounding": [
                {
                    "field": "content",
                    "confidence": "high",
                    "citations": [{"url": "https://x.com", "title": "R1"}],
                }
            ],
        },
    }

    with patch("mcp_server_metasearch.tools.exa_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test", type="deep")

    assert "## Synthesized Output" in result
    assert "Synthesized answer here" in result
    assert "### Grounding" in result
    assert "confidence: high" in result


def test_format_search_results_empty():
    """Formatter should handle empty results gracefully."""
    result = _format_search_results({})
    assert result == "No results."
