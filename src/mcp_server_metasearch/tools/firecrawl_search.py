"""Firecrawl Search tool."""

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, join_lines

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"

SUPPORTED_SOURCES = ("web", "news", "images")
SUPPORTED_CATEGORIES = ("github", "research", "pdf")


class FirecrawlSearchTool(BaseTool):
    name = "firecrawl_search"
    description = (
        "Use when searching with full-page scraping or category filters. Supports GitHub, research papers, PDFs, images.\n"
        "Params: query (req), limit (per source, def 5, max 50), sources (\"web\"|\"news\"|\"images\"), categories (\"github\"|\"research\"|\"pdf\"), include_domains, exclude_domains, scrape_content (extra credits)"
    )
    required_env_vars = ["FIRECRAWL_API_KEY"]
    enabled_env_var = "TOOL_FIRECRAWL_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        limit: int = 5,
        sources: list[str] | None = None,
        categories: list[str] | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        scrape_content: bool = False,
    ) -> str:
        """Search the web via Firecrawl.

        Args:
            query: Natural language search query.
            limit: Number of results per source type (default 5, max 50).
            sources: Result types to include. "web" (default), "news",
                "images". Multiple sources can be requested.
            categories: Filter by content category. "github" (repositories),
                "research" (academic papers), "pdf" (PDF documents).
            include_domains: Restrict results to these domains only.
            exclude_domains: Exclude results from these domains.
            scrape_content: If True, fetch full-page markdown content for
                each result (consumes additional credits).
        """
        api_key = get_settings().firecrawl_api_key

        # Validate sources
        normalized_sources = []
        if sources is None:
            sources = ["web"]
        for src in sources:
            src_lower = src.lower().strip()
            if src_lower not in SUPPORTED_SOURCES:
                raise ValueError(
                    f"Unsupported source: {src!r}. "
                    f"Supported: {', '.join(SUPPORTED_SOURCES)}"
                )
            normalized_sources.append(src_lower)
        if not normalized_sources:
            normalized_sources = ["web"]

        # Validate categories
        normalized_categories = None
        if categories:
            normalized_categories = []
            for cat in categories:
                cat_lower = cat.lower().strip()
                if cat_lower not in SUPPORTED_CATEGORIES:
                    raise ValueError(
                        f"Unsupported category: {cat!r}. "
                        f"Supported: {', '.join(SUPPORTED_CATEGORIES)}"
                    )
                normalized_categories.append(cat_lower)

        payload: dict[str, object] = {
            "query": query,
            "limit": max(1, min(50, limit)),
            "sources": normalized_sources,
        }

        if normalized_categories:
            payload["categories"] = normalized_categories
        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        if scrape_content:
            payload["scrapeOptions"] = {
                "formats": ["markdown"],
                "onlyMainContent": True,
            }

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            FIRECRAWL_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_search_results(data, scrape_content)


def _format_search_results(data: dict, scrape_content: bool) -> str:
    """Format Firecrawl search JSON response into human-readable text."""
    lines: list[str] = []

    success = data.get("success", False)
    if not success:
        lines.append("Search failed.")
        warning = data.get("warning")
        if warning:
            lines.append(f"Warning: {warning}")
        return "\n".join(lines)

    result_data = data.get("data", {})
    credits_used = data.get("creditsUsed")

    # Web results
    web_results = result_data.get("web", [])
    if web_results:
        lines.append(f"## Web Results ({len(web_results)})")
        for idx, result in enumerate(web_results, 1):
            lines.append(_format_result(result, idx, scrape_content))
        lines.append("")

    # News results
    news_results = result_data.get("news", [])
    if news_results:
        lines.append(f"## News Results ({len(news_results)})")
        for idx, result in enumerate(news_results, 1):
            lines.append(_format_result(result, idx, scrape_content))
        lines.append("")

    # Image results
    image_results = result_data.get("images", [])
    if image_results:
        lines.append(f"## Image Results ({len(image_results)})")
        for idx, result in enumerate(image_results, 1):
            title = result.get("title", "Untitled")
            image_url = result.get("imageUrl", "")
            source_url = result.get("url", "")
            width = result.get("imageWidth", "")
            height = result.get("imageHeight", "")
            dims = f" ({width}x{height})" if width and height else ""
            lines.append(f"{idx}. {title}{dims}")
            if image_url:
                lines.append(f"   Image: {image_url}")
            if source_url:
                lines.append(f"   Source: {source_url}")
            lines.append("")

    if credits_used is not None:
        lines.append(f"Credits used: {credits_used}")

    warning = data.get("warning")
    if warning:
        lines.append(f"Warning: {warning}")

    return join_lines(lines, "No results found.")


def _format_result(result: dict, idx: int, scrape_content: bool) -> str:
    """Format a single search result."""
    lines: list[str] = []
    title = result.get("title", "Untitled")
    url = result.get("url", "")
    description = result.get("description", "")
    category = result.get("category", "")

    lines.append(f"{idx}. {title}")
    append_if(lines, "URL", url)
    append_if(lines, "Description", description)
    append_if(lines, "Category", category)

    if scrape_content:
        markdown = result.get("markdown")
        if markdown:
            lines.append("   Content:")
            # Indent content for readability
            for content_line in markdown.split("\n"):
                lines.append(f"      {content_line}")

    links = result.get("links")
    if links:
        lines.append("   Links:")
        for link in links[:10]:  # Limit links per result
            lines.append(f"      - {link}")

    return "\n".join(lines)
