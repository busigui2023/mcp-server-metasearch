"""Tests for Tavily Research tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_metasearch.tools.tavily_research import (
    TavilyResearchTool,
    _format_research_results,
    _poll_research_status,
)


@pytest.fixture
def tool():
    return TavilyResearchTool()


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


async def test_call_success(tool, mock_settings):
    """Successful research should return formatted report."""
    create_response = _make_response({
        "request_id": "req-789",
        "status": "pending",
    })

    status_response = _make_response({
        "request_id": "req-789",
        "status": "completed",
        "content": "AI is advancing rapidly.",
        "sources": [
            {"title": "AI News", "url": "https://ai.com", "favicon": "https://ai.com/favicon.ico"},
        ],
        "created_at": "2025-01-15T10:30:00Z",
        "response_time": 45.2,
    })

    with patch("mcp_server_metasearch.tools.tavily_research.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                # Patch POLL_INTERVAL to avoid real sleep in tests
                with patch("mcp_server_metasearch.tools.tavily_research.POLL_INTERVAL_SECONDS", 0):
                    result = await tool.call(input="Latest AI developments")

    assert "# Research Report" in result
    assert "AI is advancing rapidly." in result
    assert "## Sources" in result
    assert "AI News" in result
    assert "https://ai.com" in result
    assert "Request ID: req-789" in result

    # Verify creation payload
    payload = mock_post.call_args.kwargs["json"]
    assert payload["input"] == "Latest AI developments"
    assert payload["model"] == "auto"
    assert payload["citation_format"] == "numbered"


async def test_call_missing_request_id(tool, mock_settings):
    """If creation response lacks request_id, raise RuntimeError."""
    create_response = _make_response({"status": "pending"})  # no request_id

    with patch("mcp_server_metasearch.tools.tavily_research.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with pytest.raises(RuntimeError, match="no request_id"):
                await tool.call(input="test")


async def test_call_failed_research(tool, mock_settings):
    """Failed research task should report failure."""
    create_response = _make_response({"request_id": "req-fail", "status": "pending"})
    status_response = _make_response({"request_id": "req-fail", "status": "failed"})

    with patch("mcp_server_metasearch.tools.tavily_research.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch("mcp_server_metasearch.tools.tavily_research.POLL_INTERVAL_SECONDS", 0):
                    result = await tool.call(input="test")

    assert "## Research Failed" in result
    assert "req-fail" in result


async def test_call_timeout(tool, mock_settings):
    """Polling timeout should return status message with request_id."""
    create_response = _make_response({"request_id": "req-timeout", "status": "pending"})

    # Status stays in_progress forever
    status_response = _make_response({"request_id": "req-timeout", "status": "in_progress"})

    with patch("mcp_server_metasearch.tools.tavily_research.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                # Reduce max attempts for faster test
                with patch("mcp_server_metasearch.tools.tavily_research.POLL_INTERVAL_SECONDS", 0):
                    with patch("mcp_server_metasearch.tools.tavily_research.MAX_POLL_ATTEMPTS", 2):
                        result = await tool.call(input="test")

    assert "still in progress" in result
    assert "req-timeout" in result


async def test_poll_research_status_completed():
    """Poll should return immediately when status is completed."""
    status_response = _make_response({
        "request_id": "req-1",
        "status": "completed",
        "content": "Done",
    })

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = status_response
        with patch("mcp_server_metasearch.tools.tavily_research.POLL_INTERVAL_SECONDS", 0):
            result = await _poll_research_status("req-1", {"Authorization": "Bearer test"})

    assert result["status"] == "completed"
    assert result["content"] == "Done"
    # Should have polled once
    assert mock_get.call_count == 1


async def test_poll_research_status_eventual_completion():
    """Poll should retry until completed."""
    responses = [
        _make_response({"request_id": "req-2", "status": "pending"}),
        _make_response({"request_id": "req-2", "status": "in_progress"}),
        _make_response({"request_id": "req-2", "status": "completed", "content": "Final"}),
    ]

    mock_get = AsyncMock()
    mock_get.side_effect = responses

    with patch("httpx.AsyncClient.get", mock_get):
        with patch("mcp_server_metasearch.tools.tavily_research.POLL_INTERVAL_SECONDS", 0):
            result = await _poll_research_status("req-2", {"Authorization": "Bearer test"})

    assert result["status"] == "completed"
    assert result["content"] == "Final"
    assert mock_get.call_count == 3


def test_format_research_results_timeout():
    """Formatter should handle timeout status."""
    result = _format_research_results({
        "status": "timeout",
        "request_id": "req-t",
        "message": "Task is still running.",
    })
    assert "Task is still running." in result


def test_format_research_results_structured_content():
    """Formatter should handle non-string content (e.g. JSON schema output)."""
    result = _format_research_results({
        "status": "completed",
        "request_id": "req-3",
        "content": {"company": "Tavily", "metrics": ["fast", "accurate"]},
        "sources": [],
    })
    assert "Tavily" in result
