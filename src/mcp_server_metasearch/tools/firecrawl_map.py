"""Firecrawl Map tool."""

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import join_lines

FIRECRAWL_MAP_URL = "https://api.firecrawl.dev/v2/map"


class FirecrawlMapTool(BaseTool):
    name = "firecrawl_map"
    description = (
        "Use when discovering all URLs on a site before crawling. Costs 1 credit regardless of count.\n"
        "Params: url (req), limit (def 100), search (keyword filter)"
    )
    required_env_vars = ["FIRECRAWL_API_KEY"]
    enabled_env_var = "TOOL_FIRECRAWL_MAP_ENABLED"

    async def call(
        self,
        url: str,
        limit: int = 100,
        search: str | None = None,
    ) -> str:
        """Map all URLs on a website via Firecrawl.

        Args:
            url: The website URL to map (e.g., "https://docs.example.com").
            limit: Maximum number of URLs to return (default 100).
            search: Optional keyword to filter URLs by relevance within
                the site.
        """
        api_key = get_settings().firecrawl_api_key

        payload: dict[str, object] = {
            "url": url,
            "limit": max(1, min(10000, limit)),
        }

        if search:
            payload["search"] = search

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            FIRECRAWL_MAP_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_map_results(data, url)


def _format_map_results(data: dict, original_url: str) -> str:
    """Format Firecrawl map JSON response into human-readable text."""
    lines: list[str] = []

    success = data.get("success", False)
    if not success:
        lines.append("Map failed.")
        return join_lines(lines, "")

    links = data.get("links", [])

    if not links:
        lines.append(f"No URLs found on {original_url}.")
        return "\n".join(lines)

    lines.append(f"Found {len(links)} URLs on {original_url}:")
    lines.append("")

    for idx, link in enumerate(links, 1):
        if isinstance(link, str):
            lines.append(f"{idx}. {link}")
        elif isinstance(link, dict):
            url = link.get("url", "")
            title = link.get("title", "")
            description = link.get("description", "")

            display = f"{idx}. "
            if title:
                display += title
            else:
                display += url or "Unknown"
            lines.append(display)

            if url and title:
                lines.append(f"   URL: {url}")
            if description:
                lines.append(f"   Description: {description}")
        else:
            lines.append(f"{idx}. {str(link)}")

    return "\n".join(lines)
