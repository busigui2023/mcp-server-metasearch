"""Tests for Firecrawl Crawl tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server_metasearch.tools.firecrawl_crawl import (
    FirecrawlCrawlTool,
    _format_crawl_results,
    _poll_crawl_status,
)


@pytest.fixture
def tool():
    return FirecrawlCrawlTool()


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.firecrawl_api_key = "fc-test-key"
    return settings


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    mock.text = str(data)
    return mock


async def test_call_success(tool, mock_settings):
    """Successful crawl should return formatted page list."""
    create_response = _make_response({
        "success": True,
        "id": "crawl-123",
        "url": "https://api.firecrawl.dev/v2/crawl/crawl-123",
    })

    status_response = _make_response({
        "status": "completed",
        "id": "crawl-123",
        "total": 2,
        "completed": 2,
        "creditsUsed": 2,
        "data": [
            {
                "markdown": "# Page 1\nContent 1",
                "metadata": {
                    "title": "Page One",
                    "sourceURL": "https://example.com/1",
                    "statusCode": 200,
                },
            },
            {
                "markdown": "# Page 2\nContent 2",
                "metadata": {
                    "title": "Page Two",
                    "sourceURL": "https://example.com/2",
                    "statusCode": 200,
                },
            },
        ],
    })

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    result = await tool.call(url="https://example.com")

    assert "Crawl Status: completed" in result
    assert "Pages: 2/2" in result
    assert "Credits: 2" in result
    assert "Page One" in result
    assert "https://example.com/1" in result
    assert "Content 1" in result
    assert "Page Two" in result

    payload = mock_post.call_args.kwargs["json"]
    assert payload["url"] == "https://example.com"
    assert payload["limit"] == 10
    assert payload["scrapeOptions"]["formats"] == ["markdown"]


async def test_call_with_options(tool, mock_settings):
    """Optional parameters should be included in payload."""
    create_response = _make_response({"success": True, "id": "crawl-456"})
    status_response = _make_response({
        "status": "completed",
        "id": "crawl-456",
        "total": 1,
        "completed": 1,
        "creditsUsed": 1,
        "data": [],
    })

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    await tool.call(
                        url="https://example.com",
                        limit=20,
                        max_discovery_depth=3,
                        include_paths=["/docs/.*"],
                        exclude_paths=["/blog/.*"],
                        allow_subdomains=True,
                        formats=["markdown", "links"],
                    )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["limit"] == 20
    assert payload["maxDiscoveryDepth"] == 3
    assert payload["includePaths"] == ["/docs/.*"]
    assert payload["excludePaths"] == ["/blog/.*"]
    assert payload["allowSubdomains"] is True
    assert payload["scrapeOptions"]["formats"] == ["markdown", "links"]


async def test_call_limit_clamped(tool, mock_settings):
    """limit should be clamped to 1-100 range."""
    create_response = _make_response({"success": True, "id": "crawl-789"})
    status_response = _make_response({
        "status": "completed",
        "id": "crawl-789",
        "total": 0,
        "completed": 0,
        "creditsUsed": 0,
        "data": [],
    })

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    await tool.call(url="https://x.com", limit=200)
                    payload = mock_post.call_args.kwargs["json"]
                    assert payload["limit"] == 100

                    await tool.call(url="https://x.com", limit=0)
                    payload = mock_post.call_args.kwargs["json"]
                    assert payload["limit"] == 1


async def test_call_missing_crawl_id(tool, mock_settings):
    """If creation response lacks id, raise RuntimeError."""
    create_response = _make_response({"success": True})  # no id

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with pytest.raises(RuntimeError, match="no id"):
                await tool.call(url="https://x.com")


async def test_call_failed_crawl(tool, mock_settings):
    """Failed crawl should report failure."""
    create_response = _make_response({"success": True, "id": "crawl-fail"})
    status_response = _make_response({
        "status": "failed",
        "id": "crawl-fail",
    })

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    result = await tool.call(url="https://x.com")

    assert "## Crawl Failed" in result
    assert "crawl-fail" in result


async def test_call_timeout(tool, mock_settings):
    """Polling timeout should return status message."""
    create_response = _make_response({"success": True, "id": "crawl-t"})
    status_response = _make_response({"status": "scraping", "id": "crawl-t"})

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    with patch(
                        "mcp_server_metasearch.tools.firecrawl_crawl.MAX_POLL_ATTEMPTS",
                        2,
                    ):
                        result = await tool.call(url="https://x.com")

    assert "still in progress" in result
    assert "crawl-t" in result


async def test_call_cancelled(tool, mock_settings):
    """Cancelled crawl should report cancellation."""
    create_response = _make_response({"success": True, "id": "crawl-can"})
    status_response = _make_response({"status": "cancelled", "id": "crawl-can"})

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = create_response
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = status_response
                with patch(
                    "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS",
                    0,
                ):
                    result = await tool.call(url="https://x.com")

    assert "## Crawl Cancelled" in result


async def test_poll_crawl_status_completed():
    """Poll should return immediately when status is completed."""
    status_response = _make_response({"status": "completed", "id": "c-1"})

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = status_response
        with patch(
            "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS", 0
        ):
            result = await _poll_crawl_status("c-1", {"Authorization": "Bearer test"})

    assert result["status"] == "completed"
    assert mock_get.call_count == 1


async def test_poll_crawl_status_eventual_completion():
    """Poll should retry until completed."""
    responses = [
        _make_response({"status": "scraping", "id": "c-2"}),
        _make_response({"status": "scraping", "id": "c-2"}),
        _make_response({"status": "completed", "id": "c-2", "total": 1}),
    ]

    mock_get = AsyncMock()
    mock_get.side_effect = responses

    with patch("httpx.AsyncClient.get", mock_get):
        with patch(
            "mcp_server_metasearch.tools.firecrawl_crawl.POLL_INTERVAL_SECONDS", 0
        ):
            result = await _poll_crawl_status("c-2", {"Authorization": "Bearer test"})

    assert result["status"] == "completed"
    assert mock_get.call_count == 3


async def test_call_http_error(tool, mock_settings):
    """HTTP errors should propagate as exceptions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "402 Payment Required",
        request=MagicMock(),
        response=MagicMock(status_code=402),
    )

    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(httpx.HTTPStatusError):
                await tool.call(url="https://x.com")


async def test_call_invalid_format(tool, mock_settings):
    """Invalid format should raise ValueError."""
    with patch(
        "mcp_server_metasearch.tools.firecrawl_crawl.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(ValueError, match="Unsupported format"):
            await tool.call(url="https://x.com", formats=["invalid"])


def test_format_crawl_results_timeout():
    """Formatter should handle timeout status."""
    result = _format_crawl_results({
        "status": "timeout",
        "id": "c-t",
        "message": "Still crawling...",
    })
    assert "Still crawling..." in result


def test_format_crawl_results_empty():
    """Formatter should handle empty crawl data."""
    result = _format_crawl_results({
        "status": "completed",
        "id": "c-e",
        "total": 0,
        "completed": 0,
        "creditsUsed": 0,
        "data": [],
    })
    assert "Crawl Status: completed" in result
    assert "Pages: 0/0" in result
