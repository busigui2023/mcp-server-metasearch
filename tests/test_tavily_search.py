"""Tests for Tavily Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.tavily_search import TavilySearchTool, _format_search_results


@pytest.fixture
def tool():
    return TavilySearchTool()


@pytest.fixture
def mock_settings():
    """Return a mock settings object with tavily_api_key set."""
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


async def test_call_success(tool, mock_settings):
    """Successful search should return formatted results."""
    mock_response_data = {
        "query": "Who is Leo Messi?",
        "answer": "Lionel Messi is an Argentine footballer.",
        "results": [
            {
                "title": "Lionel Messi Facts",
                "url": "https://example.com/messi",
                "content": "Messi is a footballer.",
                "score": 0.95,
            }
        ],
        "images": [],
        "usage": {"credits": 1},
        "request_id": "req-123",
    }

    mock_response = _make_response(mock_response_data)

    with patch("mcp_server_metasearch.tools.tavily_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await tool.call(query="Who is Leo Messi?")

    assert "Query: Who is Leo Messi?" in result
    assert "## Answer" in result
    assert "Lionel Messi is an Argentine footballer." in result
    assert "Lionel Messi Facts" in result
    assert "https://example.com/messi" in result
    assert "Score: 0.9500" in result
    assert "Credits used: 1" in result
    assert "Request ID: req-123" in result


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch("mcp_server_metasearch.tools.tavily_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


async def test_call_with_optional_params(tool, mock_settings):
    """Optional parameters should be included in the payload."""
    mock_response = _make_response({"query": "test", "results": []})

    with patch("mcp_server_metasearch.tools.tavily_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await tool.call(
                query="test",
                search_depth="advanced",
                max_results=10,
                topic="news",
                time_range="week",
                include_answer=True,
                include_raw_content=True,
                include_images=True,
                include_favicon=True,
                include_domains=["example.com"],
                exclude_domains=["spam.com"],
            )

    call_args = mock_post.call_args
    payload = call_args.kwargs["json"]

    assert payload["search_depth"] == "advanced"
    assert payload["max_results"] == 10
    assert payload["topic"] == "news"
    assert payload["time_range"] == "week"
    assert payload["include_answer"] is True
    assert payload["include_raw_content"] is True
    assert payload["include_images"] is True
    assert payload["include_favicon"] is True
    assert payload["include_domains"] == ["example.com"]
    assert payload["exclude_domains"] == ["spam.com"]


async def test_call_max_results_clamped(tool, mock_settings):
    """max_results should be clamped to 0-20 range."""
    mock_response = _make_response({"query": "test", "results": []})

    with patch("mcp_server_metasearch.tools.tavily_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            await tool.call(query="test", max_results=50)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["max_results"] == 20

            await tool.call(query="test", max_results=-5)
            payload = mock_post.call_args.kwargs["json"]
            assert payload["max_results"] == 0


def test_format_search_results_with_images():
    """Formatter should handle image results correctly."""
    data = {
        "query": "cats",
        "results": [],
        "images": [
            {"url": "https://example.com/cat.jpg", "description": "A cute cat"},
            "https://example.com/kitten.jpg",
        ],
    }
    result = _format_search_results(data)
    assert "## Images (2)" in result
    assert "https://example.com/cat.jpg (A cute cat)" in result
    assert "https://example.com/kitten.jpg" in result


def test_format_search_results_empty():
    """Formatter should handle empty results gracefully."""
    result = _format_search_results({})
    assert result == "No results."
