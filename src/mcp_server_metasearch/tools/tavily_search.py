"""Tavily Search tool."""

from typing import Literal

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, append_numbered, join_lines

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilySearchTool(BaseTool):
    name = "tavily_search"
    description = (
        "Use when you need filtered search with time/topic/domain controls.\n"
        "Params: query (req), search_depth (\"basic\"|\"fast\"|\"advanced\"(2c)|\"ultra-fast\"), max_results (0-20, def 5), topic (\"general\"|\"news\"|\"finance\"), time_range (\"day\"|\"week\"|\"month\"|\"year\"), include_answer, include_raw_content, include_images, include_favicon, include_domains (max 300), exclude_domains (max 150)"
    )
    required_env_vars = ["TAVILY_API_KEY"]
    enabled_env_var = "TOOL_TAVILY_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        search_depth: Literal["basic", "fast", "advanced", "ultra-fast"] = "basic",
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        time_range: Literal["day", "week", "month", "year"] | None = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        include_favicon: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> str:
        """Search the web via Tavily.

        Args:
            query: Search keywords or natural-language question.
            search_depth: Latency vs relevance tradeoff. "basic" (default),
                "fast", "advanced" (2 credits), "ultra-fast".
            max_results: Number of results to return (0-20). Default 5.
            topic: Search category. "general" (default), "news", or "finance".
            time_range: Filter by recency. "day", "week", "month", or "year".
            include_answer: Include an LLM-generated answer to the query.
            include_raw_content: Include full cleaned page content per result.
            include_images: Include images from search results.
            include_favicon: Include favicon URLs per result.
            include_domains: Domains to restrict results to (max 300).
            exclude_domains: Domains to exclude from results (max 150).
        """
        settings = get_settings()

        payload: dict[str, object] = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max(0, min(20, max_results)),
            "topic": topic,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_favicon": include_favicon,
        }

        if time_range is not None:
            payload["time_range"] = time_range
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            TAVILY_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_search_results(data)


def _format_search_results(data: dict) -> str:
    """Format Tavily search JSON response into human-readable text."""
    lines: list[str] = []

    query = data.get("query", "")
    if query:
        lines.append(f"Query: {query}")
        lines.append("")

    answer = data.get("answer")
    if answer:
        lines.append("## Answer")
        lines.append(str(answer))
        lines.append("")

    results = data.get("results", [])
    if results:
        lines.append(f"## Results ({len(results)})")
        for idx, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            score = result.get("score")
            content = result.get("content", "")
            raw = result.get("raw_content")
            favicon = result.get("favicon")

            lines.append("")
            append_numbered(lines, idx, title)
            append_if(lines, "URL", url)
            if score is not None:
                append_if(lines, "Score", f"{score:.4f}")
            append_if(lines, "Favicon", favicon)
            append_if(lines, "Summary", content)
            if raw:
                lines.append(f"   Raw Content:\n{raw}")

    images = data.get("images", [])
    if images:
        lines.append("")
        lines.append(f"## Images ({len(images)})")
        for img in images:
            if isinstance(img, dict):
                url = img.get("url", "")
                desc = img.get("description", "")
                lines.append(f"- {url}" + (f" ({desc})" if desc else ""))
            else:
                lines.append(f"- {img}")

    usage = data.get("usage")
    if usage:
        lines.append("")
        lines.append(f"Credits used: {usage.get('credits', 'unknown')}")

    request_id = data.get("request_id")
    if request_id:
        lines.append(f"Request ID: {request_id}")

    return join_lines(lines)
