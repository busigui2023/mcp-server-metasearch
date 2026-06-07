"""Shared HTTP client for connection pool reuse across all tools."""

import atexit
import asyncio

import httpx

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a shared AsyncClient instance for connection pooling.

    The client is created lazily on first call and reused across all
    tool invocations for the lifetime of the server process.
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
        atexit.register(_close_client)
    return _http_client


def _close_client() -> None:
    """Close the global HTTP client, attempting async then sync fallback."""
    global _http_client
    if _http_client is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_http_client.aclose())
            else:
                loop.run_until_complete(_http_client.aclose())
        except RuntimeError:
            pass
        _http_client = None
