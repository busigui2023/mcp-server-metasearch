"""Tests for Bocha AI Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.bocha_ai_search import (
    BochaAiSearchTool,
    _format_ai_search_results,
)


@pytest.fixture
def tool():
    return BochaAiSearchTool()


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
    """Successful AI search should return formatted results with modal cards."""
    mock_data = {
        "code": 200,
        "log_id": "log-456",
        "messages": [
            {
                "role": "assistant",
                "type": "source",
                "content_type": "webpage",
                "content": '{"webSearchUrl":"https://bochaai.com/search?q=test","value":[{"name":"AI Search Result","url":"https://ai.example.com","snippet":"AI snippet","siteName":"AI Site"}]}',
            },
            {
                "role": "assistant",
                "type": "answer",
                "content_type": "text",
                "content": "This is the AI-generated answer.",
            },
            {
                "role": "assistant",
                "type": "follow_up",
                "content_type": "text",
                "content": '["What about tomorrow?", "How does it work?"]',
            },
        ],
    }

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="北京天气", answer=True)

    assert "AI Search Result" in result
    assert "网页结果 (1" in result
    assert "AI Search Result" in result
    assert "AI 总结答案" in result
    assert "This is the AI-generated answer." in result
    assert "你可能还想问" in result
    assert "What about tomorrow?" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["query"] == "北京天气"
    assert payload["answer"] is True
    assert payload["stream"] is False


async def test_call_without_answer(tool, mock_settings):
    """Search without answer should not include AI answer section."""
    mock_data = {
        "code": 200,
        "messages": [
            {
                "role": "assistant",
                "type": "source",
                "content_type": "webpage",
                "content": '{"value":[{"name":"Result","url":"https://x.com","snippet":"S"}]}',
            },
        ],
    }

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test")

    assert "AI 总结答案" not in result
    assert "你可能还想问" not in result
    assert "Result" in result


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be included in payload."""
    mock_data = {"code": 200, "data": {"webPages": {"value": []}}}

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            await tool.call(
                query="test",
                count=20,
                freshness="oneMonth",
                answer=True,
            )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["count"] == 20
    assert payload["freshness"] == "oneMonth"
    assert payload["answer"] is True
    assert payload["stream"] is False


async def test_call_count_clamped(tool, mock_settings):
    """count should be clamped to 1-50 range."""
    mock_data = {"code": 200, "data": {"webPages": {"value": []}}}

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
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
        "429 Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


async def test_call_api_error(tool, mock_settings):
    """API error response should be formatted."""
    mock_data = {"code": 403, "msg": "Quota exceeded"}

    with patch(
        "mcp_server_metasearch.tools.bocha_ai_search.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test")

    assert "AI Search failed" in result
    assert "Quota exceeded" in result


def test_format_ai_search_results_empty():
    """Formatter should handle empty results."""
    result = _format_ai_search_results({"code": 200, "data": {}})
    assert "No results found" in result


def test_format_ai_search_results_api_error():
    """Formatter should handle API error."""
    result = _format_ai_search_results({"code": 500, "msg": "Server error"})
    assert "AI Search failed" in result
