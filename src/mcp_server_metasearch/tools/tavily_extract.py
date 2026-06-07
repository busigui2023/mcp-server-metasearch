"""Tavily Extract tool."""

from typing import Literal

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, join_lines

TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"


class TavilyExtractTool(BaseTool):
    name = "tavily_extract"
    description = (
        "Use when batch-extracting content from multiple URLs.\n"
        "Params: urls (req), query (rerank intent), extract_depth (\"basic\"|\"advanced\"), return_format (\"markdown\"|\"text\")"
    )
    required_env_vars = ["TAVILY_API_KEY"]
    enabled_env_var = "TOOL_TAVILY_EXTRACT_ENABLED"

    async def call(
        self,
        urls: str | list[str],
        query: str | None = None,
        extract_depth: Literal["basic", "advanced"] = "basic",
        return_format: Literal["markdown", "text"] = "markdown",
    ) -> str:
        """Extract content from URLs via Tavily.

        Args:
            urls: A single URL or a list of URLs to extract content from.
            query: User intent for reranking extracted chunks. When provided,
                chunks are reranked based on relevance to this query.
            extract_depth: "basic" (default) or "advanced" for more data
                including tables and embedded content.
            return_format: Output format. "markdown" (default) or "text".
        """
        settings = get_settings()

        # Normalize urls to list for the API
        url_list = [urls] if isinstance(urls, str) else urls

        payload: dict[str, object] = {
            "urls": url_list,
            "extract_depth": extract_depth,
            "format": return_format,
        }

        if query is not None:
            payload["query"] = query

        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            TAVILY_EXTRACT_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_extract_results(data)


def _format_extract_results(data: dict) -> str:
    """Format Tavily extract JSON response into human-readable text."""
    lines: list[str] = []

    results = data.get("results", [])
    if results:
        lines.append(f"## Extracted Content ({len(results)} URL(s))")
        for result in results:
            url = result.get("url", "")
            raw_content = result.get("raw_content", "")
            images = result.get("images", [])
            favicon = result.get("favicon")

            lines.append(f"\n### {url}")
            append_if(lines, "Favicon", favicon, indent="")
            if raw_content:
                lines.append(raw_content)
            if images:
                lines.append(f"\nImages: {', '.join(str(i) for i in images)}")

    failed = data.get("failed_results", [])
    if failed:
        lines.append("")
        lines.append(f"## Failed URLs ({len(failed)})")
        for item in failed:
            url = item.get("url", "")
            error = item.get("error", "Unknown error")
            lines.append(f"- {url}: {error}")

    usage = data.get("usage")
    if usage:
        lines.append("")
        lines.append(f"Credits used: {usage.get('credits', 'unknown')}")

    request_id = data.get("request_id")
    if request_id:
        lines.append(f"Request ID: {request_id}")

    return join_lines(lines, "No extraction results.")
