"""Tests for Exa Answer tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.exa_answer import ExaAnswerTool, _format_answer_results


@pytest.fixture
def tool():
    return ExaAnswerTool()


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
    """Successful answer should return formatted result."""
    mock_data = {
        "requestId": "req-444",
        "answer": "Paris is the capital of France.",
        "citations": [
            {
                "title": "France Facts",
                "url": "https://example.com/france",
                "author": "Jane Doe",
                "publishedDate": "2024-01-01",
            }
        ],
        "costDollars": {"total": 0.005},
    }

    with patch("mcp_server_metasearch.tools.exa_answer.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="What is the capital of France?")

    assert "## Answer" in result
    assert "Paris is the capital of France." in result
    assert "## Sources (1)" in result
    assert "France Facts" in result
    assert "https://example.com/france" in result
    assert "Jane Doe" in result
    assert "Cost: $0.005" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["query"] == "What is the capital of France?"
    assert payload["text"] is False


async def test_call_with_text(tool, mock_settings):
    """text=True should include source text in payload."""
    mock_data = {
        "requestId": "req-555",
        "answer": "Yes",
        "citations": [
            {
                "title": "T",
                "url": "https://x.com",
                "text": "Full source text here...",
            }
        ],
    }

    with patch("mcp_server_metasearch.tools.exa_answer.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(mock_data)
            result = await tool.call(query="test", text=True)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["text"] is True
    assert "Full source text here..." in result


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )

    with patch("mcp_server_metasearch.tools.exa_answer.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


def test_format_answer_results_empty():
    """Formatter should handle empty response."""
    result = _format_answer_results({})
    assert result == "No answer."
