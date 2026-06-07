"""Exa Search tool."""

from typing import Literal

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, append_numbered, join_lines

EXA_API_URL = "https://api.exa.ai/search"

SEARCH_TYPES = ("auto", "fast", "instant", "deep-lite", "deep", "deep-reasoning")
CATEGORIES = (
    "company",
    "people",
    "research paper",
    "news",
    "personal site",
    "financial report",
)
CONTENT_MODES = ("highlights", "text", "summary")


class ExaSearchTool(BaseTool):
    name = "exa_search"
    description = (
        "Use when you need token-efficient search. Returns highlights by default.\n"
        "Params: query (req), type (\"auto\"|\"fast\"|\"instant\"|\"deep-lite\"|\"deep\"|\"deep-reasoning\"), num_results (1-100, def 10), category (\"company\"|\"people\"|\"research paper\"|\"news\"|\"personal site\"|\"financial report\"), content_mode (\"highlights\"|\"text\"|\"summary\"), include_domains (max 1200), exclude_domains (max 1200), max_age_hours (0=live, -1=cache)"
    )
    required_env_vars = ["EXA_API_KEY"]
    enabled_env_var = "TOOL_EXA_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        # NOTE: 'type' matches the Exa API field name; despite shadowing the
        # Python builtin, changing it would break JSON Schema for MCP clients.
        type: Literal["auto", "fast", "instant", "deep-lite", "deep", "deep-reasoning"] = "auto",
        num_results: int = 10,
        category: Literal[
            "company",
            "people",
            "research paper",
            "news",
            "personal site",
            "financial report",
        ] | None = None,
        content_mode: Literal["highlights", "text", "summary"] = "highlights",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        max_age_hours: int | None = None,
    ) -> str:
        """Search the web via Exa.

        Args:
            query: Natural language search query.
            type: Search method. "auto" (default), "fast", "instant",
                "deep-lite", "deep", or "deep-reasoning".
            num_results: Number of results to return (1-100). Default 10.
            category: Focus on specific content type. "company", "people",
                "research paper", "news", "personal site", or "financial report".
                Note: "company" and "people" do not support exclude_domains
                or date filters.
            content_mode: What content to return per result. "highlights"
                (default, most token-efficient), "text" (full page), or
                "summary" (LLM-generated abstract).
            include_domains: Only return results from these domains (max 1200).
            exclude_domains: Exclude results from these domains (max 1200).
            max_age_hours: Content freshness. 0 = always livecrawl.
                -1 = cache only. Omit for default behavior.
        """
        api_key = get_settings().exa_api_key or ""

        payload: dict[str, object] = {
            "query": query,
            "type": type,
            "numResults": max(1, min(100, num_results)),
        }

        # Build contents sub-object
        contents: dict[str, object] = {}
        if content_mode == "highlights":
            contents["highlights"] = True
        elif content_mode == "text":
            contents["text"] = True
        elif content_mode == "summary":
            contents["summary"] = True

        if max_age_hours is not None:
            contents["maxAgeHours"] = max_age_hours

        if contents:
            payload["contents"] = contents

        if category is not None:
            payload["category"] = category
        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        headers: dict[str, str] = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            EXA_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_search_results(data)


def _format_search_results(data: dict) -> str:
    """Format Exa search JSON response into human-readable text."""
    lines: list[str] = []

    request_id = data.get("requestId", "")
    search_type = data.get("searchType", "")
    if search_type:
        lines.append(f"Search Type: {search_type}")
    if request_id:
        lines.append(f"Request ID: {request_id}")
        lines.append("")

    results = data.get("results", [])
    if results:
        lines.append(f"## Results ({len(results)})")
        for idx, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            author = result.get("author")
            published = result.get("publishedDate")
            favicon = result.get("favicon")

            lines.append("")
            append_numbered(lines, idx, title)
            append_if(lines, "URL", url)
            append_if(lines, "Author", author)
            append_if(lines, "Published", published)
            append_if(lines, "Favicon", favicon)

            highlights = result.get("highlights")
            if highlights:
                lines.append("   Highlights:")
                for h in highlights:
                    lines.append(f"     - {h}")

            text = result.get("text")
            if text:
                lines.append(f"   Text:\n{text}")

            summary = result.get("summary")
            if summary:
                lines.append(f"   Summary: {summary}")

            subpages = result.get("subpages", [])
            if subpages:
                lines.append(f"   Subpages: {len(subpages)}")

    # Synthesized output (deep search)
    output = data.get("output")
    if output:
        lines.append("")
        lines.append("## Synthesized Output")
        content = output.get("content")
        if content is not None:
            if isinstance(content, str):
                lines.append(content)
            else:
                lines.append(str(content))

        grounding = output.get("grounding", [])
        if grounding:
            lines.append("")
            lines.append("### Grounding")
            for g in grounding:
                field = g.get("field", "")
                confidence = g.get("confidence", "")
                citations = g.get("citations", [])
                lines.append(f"Field: {field} (confidence: {confidence})")
                for c in citations:
                    lines.append(f"  - {c.get('title', '')}: {c.get('url', '')}")

    cost = data.get("costDollars", {})
    if cost:
        lines.append("")
        lines.append(f"Cost: ${cost.get('total', 'unknown')}")

    return join_lines(lines)
