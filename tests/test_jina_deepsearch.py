"""Tests for Jina DeepSearch tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.jina_deepsearch import (
    DEEPSEARCH_API_URL,
    DEFAULT_MODEL,
    JinaDeepSearchTool,
)


@pytest.fixture
def tool():
    return JinaDeepSearchTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.jina_api_key = "jina-test-key"
    return settings


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


async def test_call_success(tool, mock_settings):
    """Successful deep search should return content from choices."""
    mock_response = _make_response({
        "choices": [
            {"message": {"content": "Deep research result"}}
        ]
    })
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await tool.call(query="What is AI?")
    assert result == "Deep research result"
    call_args = mock_post.call_args
    assert call_args.args[0] == DEEPSEARCH_API_URL
    payload = call_args.kwargs["json"]
    assert payload["model"] == DEFAULT_MODEL
    assert payload["messages"] == [{"role": "user", "content": "What is AI?"}]
    assert payload["stream"] is False
    assert payload["max_tokens"] == 4096


async def test_call_with_max_tokens(tool, mock_settings):
    """Custom max_tokens should be reflected in payload."""
    mock_response = _make_response({
        "choices": [{"message": {"content": "Result"}}]
    })
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await tool.call(query="test", max_tokens=2048)
    payload = mock_post.call_args.kwargs["json"]
    assert payload["max_tokens"] == 2048


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")


async def test_call_malformed_response_missing_choices(tool, mock_settings):
    """Missing choices key should raise RuntimeError."""
    mock_response = _make_response({"error": "bad request"})
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(RuntimeError) as exc_info:
                await tool.call(query="test")
    assert "Unexpected DeepSearch response structure" in str(exc_info.value)


async def test_call_malformed_response_empty_choices(tool, mock_settings):
    """Empty choices list should raise RuntimeError."""
    mock_response = _make_response({"choices": []})
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(RuntimeError) as exc_info:
                await tool.call(query="test")
    assert "Unexpected DeepSearch response structure" in str(exc_info.value)


async def test_call_malformed_response_missing_message(tool, mock_settings):
    """Missing message in choice should raise RuntimeError."""
    mock_response = _make_response({"choices": [{"index": 0}]})
    with patch("mcp_server_metasearch.tools.jina_deepsearch.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(RuntimeError) as exc_info:
                await tool.call(query="test")
    assert "Unexpected DeepSearch response structure" in str(exc_info.value)
