"""Bocha Web Search tool."""

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import (
    format_bocha_web_result,
    join_lines,
)

BOCHA_WEB_SEARCH_URL = "https://api.bochaai.com/v1/web-search"


class BochaWebSearchTool(BaseTool):
    name = "bocha_web_search"
    description = (
        "Use when searching Chinese-language or China domestic content.\n"
        "Params: query (req), count (1-50, def 5), freshness (\"oneDay\"|\"oneWeek\"|\"oneMonth\"|\"oneYear\"|\"noLimit\"|\"YYYY-MM-DD..YYYY-MM-DD\"), summary (AI summary per result), include_domains, exclude_domains"
    )
    required_env_vars = ["BOCHA_API_KEY"]
    enabled_env_var = "TOOL_BOCHA_WEB_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        count: int = 5,
        freshness: str | None = None,
        summary: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> str:
        """Search the web via Bocha AI.

        Args:
            query: Natural language search query.
            count: Number of results to return (1-50). Default 5.
            freshness: Time filter. "oneDay", "oneWeek", "oneMonth",
                "oneYear", "noLimit", or a custom date range
                "YYYY-MM-DD..YYYY-MM-DD".
            summary: If True, include AI-generated summary for each result.
            include_domains: Only return results from these domains.
            exclude_domains: Exclude results from these domains.
        """
        api_key = get_settings().bocha_api_key

        payload: dict[str, object] = {
            "query": query,
            "count": max(1, min(50, count)),
        }

        if freshness is not None:
            payload["freshness"] = freshness
        if summary:
            payload["summary"] = True
        if include_domains:
            payload["include"] = include_domains
        if exclude_domains:
            payload["exclude"] = exclude_domains

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            BOCHA_WEB_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_web_search_results(data)


def _format_web_search_results(data: dict) -> str:
    """Format Bocha web search JSON response into human-readable text."""
    lines: list[str] = []

    code = data.get("code", 0)
    if code != 200:
        msg = data.get("msg", "Unknown error")
        lines.append(f"Search failed (code {code}): {msg}")
        return "\n".join(lines)

    result_data = data.get("data", {})
    web_pages = result_data.get("webPages", {})
    results = web_pages.get("value", [])

    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    total = web_pages.get("totalEstimatedMatches")
    header = f"## 搜索结果 ({len(results)}"
    if total is not None:
        header += f" / 约 {total} 条"
    header += ")"
    lines.append(header)
    lines.append("")

    for idx, result in enumerate(results, 1):
        lines.append(_format_result(result, idx))
        lines.append("")

    return join_lines(lines, "No results found.")


def _format_result(result: dict, idx: int) -> str:
    """Format a single search result."""
    return format_bocha_web_result(result, idx, include_icon=True)
