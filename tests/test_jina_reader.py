"""Tests for Jina Reader tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.jina_reader import JinaReaderTool


@pytest.fixture
def tool():
    return JinaReaderTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.jina_api_key = "jina-test-key"
    return settings


def _make_response(text: str = "Hello world", status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    mock.raise_for_status.return_value = None
    return mock


async def test_call_success(tool, mock_settings):
    """Successful read should return page content."""
    mock_response = _make_response("Extracted page content")
    with patch("mcp_server_metasearch.tools.jina_reader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await tool.call(url="https://example.com")
    assert result == "Extracted page content"
    call_args = mock_get.call_args
    assert call_args.args[0] == "https://r.jina.ai/https://example.com"
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jina-test-key"
    assert headers["Accept"] == "text/plain"
    assert "X-Respond-With" not in headers


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be passed as headers."""
    mock_response = _make_response()
    with patch("mcp_server_metasearch.tools.jina_reader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await tool.call(
                url="https://example.com",
                return_format="text",
                target_selector="h1",
                remove_selectors=".ad, .banner",
                timeout=60,
            )
    headers = mock_get.call_args.kwargs["headers"]
    assert headers["X-Respond-With"] == "text"
    assert headers["X-Target-Selector"] == "h1"
    assert headers["X-Remove-Selector"] == ".ad, .banner"
    assert headers["X-Timeout"] == "60"


async def test_call_timeout_clamped(tool, mock_settings):
    """Timeout should be clamped to 1-180 range."""
    mock_response = _make_response()
    with patch("mcp_server_metasearch.tools.jina_reader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await tool.call(url="https://example.com", timeout=500)
            headers = mock_get.call_args.kwargs["headers"]
            assert headers["X-Timeout"] == "180"
            await tool.call(url="https://example.com", timeout=0)
            headers = mock_get.call_args.kwargs["headers"]
            assert headers["X-Timeout"] == "1"


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    with patch("mcp_server_metasearch.tools.jina_reader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(url="https://example.com")
