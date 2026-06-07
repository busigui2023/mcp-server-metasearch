"""Tests for Jina Search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.jina_search import JinaSearchTool


@pytest.fixture
def tool():
    return JinaSearchTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.jina_api_key = "jina-test-key"
    return settings


def _make_response(text: str = "Search results", status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    mock.raise_for_status.return_value = None
    return mock


async def test_call_success(tool, mock_settings):
    """Successful search should return results text."""
    mock_response = _make_response("Search results")
    with patch("mcp_server_metasearch.tools.jina_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await tool.call(query="hello world")
    assert result == "Search results"
    call_args = mock_get.call_args
    assert call_args.args[0] == "https://s.jina.ai/hello%20world"
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jina-test-key"
    params = call_args.kwargs.get("params", {})
    assert params == {}


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be included in URL params and headers."""
    mock_response = _make_response()
    with patch("mcp_server_metasearch.tools.jina_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await tool.call(
                query="test",
                num_results=10,
                site="example.com",
                search_type="news",
                return_format="html",
            )
    call_args = mock_get.call_args
    params = call_args.kwargs["params"]
    assert params["num"] == 10
    assert params["site"] == "example.com"
    assert params["type"] == "news"
    headers = call_args.kwargs["headers"]
    assert headers["X-Respond-With"] == "html"


async def test_call_num_results_clamped(tool, mock_settings):
    """num_results should be clamped to 1-20 range."""
    mock_response = _make_response()
    with patch("mcp_server_metasearch.tools.jina_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await tool.call(query="test", num_results=50)
            params = mock_get.call_args.kwargs["params"]
            assert params["num"] == 20
            await tool.call(query="test", num_results=0)
            params = mock_get.call_args.kwargs["params"]
            assert params["num"] == 1


async def test_call_default_params(tool, mock_settings):
    """Default values should not add extra params or headers."""
    mock_response = _make_response()
    with patch("mcp_server_metasearch.tools.jina_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await tool.call(query="test")
    params = mock_get.call_args.kwargs.get("params", {})
    assert "num" not in params
    assert "site" not in params
    assert "type" not in params
    headers = mock_get.call_args.kwargs["headers"]
    assert "X-Respond-With" not in headers


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )
    with patch("mcp_server_metasearch.tools.jina_search.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(query="test")
