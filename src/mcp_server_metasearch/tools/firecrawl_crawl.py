"""Firecrawl Crawl tool."""

import asyncio
from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, join_lines

FIRECRAWL_CRAWL_URL = "https://api.firecrawl.dev/v2/crawl"

# Polling configuration
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 60

SUPPORTED_FORMATS = ("markdown", "html", "links")


class FirecrawlCrawlTool(BaseTool):
    name = "firecrawl_crawl"
    description = (
        "Use when recursively crawling a full website. Defaults to 10 pages to control credits.\n"
        "Params: url (req), limit (def 10, max 100, 1 credit/page), max_discovery_depth (omit=unlimited), include_paths (regex list), exclude_paths (regex list), allow_subdomains (def False), formats (\"markdown\"|\"html\"|\"links\")"
    )
    required_env_vars = ["FIRECRAWL_API_KEY"]
    enabled_env_var = "TOOL_FIRECRAWL_CRAWL_ENABLED"

    async def call(
        self,
        url: str,
        limit: int = 10,
        max_discovery_depth: int | None = None,
        include_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
        allow_subdomains: bool = False,
        formats: list[str] | None = None,
    ) -> str:
        """Crawl a website recursively via Firecrawl.

        Args:
            url: Starting URL to crawl from.
            limit: Maximum pages to crawl (default 10, max 100). Set
                conservatively to control credit usage (1 credit/page).
            max_discovery_depth: Maximum link-discovery hops from the
                starting URL. None means no depth limit.
            include_paths: Regex patterns for URL paths to include.
                Only matching paths are crawled.
            exclude_paths: Regex patterns for URL paths to exclude.
            allow_subdomains: Follow links to subdomains (default False).
            formats: Output format per page. "markdown" (default), "html",
                "links".
        """
        api_key = get_settings().firecrawl_api_key

        # Validate formats
        normalized_formats = []
        if formats is None:
            formats = ["markdown"]
        for fmt in formats:
            fmt_lower = fmt.lower().strip()
            if fmt_lower not in SUPPORTED_FORMATS:
                raise ValueError(
                    f"Unsupported format: {fmt!r}. "
                    f"Supported: {', '.join(SUPPORTED_FORMATS)}"
                )
            normalized_formats.append(fmt_lower)
        if not normalized_formats:
            normalized_formats = ["markdown"]

        payload: dict[str, object] = {
            "url": url,
            "limit": max(1, min(100, limit)),
            "scrapeOptions": {
                "formats": normalized_formats,
                "onlyMainContent": True,
            },
        }

        if max_discovery_depth is not None:
            payload["maxDiscoveryDepth"] = max(0, max_discovery_depth)
        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths
        if allow_subdomains:
            payload["allowSubdomains"] = True

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        # Step 1: Submit crawl job
        create_response = await client.post(
            FIRECRAWL_CRAWL_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        create_response.raise_for_status()
        create_data = create_response.json()

        crawl_id = create_data.get("id")
        if not crawl_id:
            raise RuntimeError(
                f"Crawl job creation failed: no id in response. "
                f"Response: {create_data}"
            )

        # Step 2: Poll for completion
        status_data = await _poll_crawl_status(crawl_id, headers)

        return _format_crawl_results(status_data)


async def _poll_crawl_status(
    crawl_id: str,
    headers: dict[str, str],
) -> dict:
    """Poll Firecrawl crawl status until completed, failed, or timeout."""
    status_url = f"{FIRECRAWL_CRAWL_URL}/{crawl_id}"

    client = get_http_client()
    for _attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

        response = await client.get(
            status_url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data: dict = response.json()

        status = data.get("status", "")

        if status in ("completed", "failed", "cancelled"):
            return data

        # Still pending or scraping — continue polling

    # Timeout: return last known state with timeout marker
    return {
        "status": "timeout",
        "id": crawl_id,
        "message": (
            f"Crawl job is still in progress after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds. "
            f"Use crawl ID '{crawl_id}' to check status later."
        ),
    }


def _format_crawl_results(data: dict) -> str:
    """Format Firecrawl crawl response into human-readable text."""
    lines: list[str] = []

    status = data.get("status", "")
    crawl_id = data.get("id", "")

    if status == "timeout":
        lines.append(data.get("message", "Crawl timed out."))
        return "\n".join(lines)

    if status == "failed":
        lines.append("## Crawl Failed")
        lines.append(f"Crawl ID: {crawl_id}")
        return "\n".join(lines)

    if status == "cancelled":
        lines.append("## Crawl Cancelled")
        lines.append(f"Crawl ID: {crawl_id}")
        return "\n".join(lines)

    if status != "completed":
        lines.append(f"## Unknown Crawl Status: {status}")
        lines.append(f"Crawl ID: {crawl_id}")
        return "\n".join(lines)

    # Summary
    total = data.get("total", 0)
    completed = data.get("completed", 0)
    credits_used = data.get("creditsUsed", 0)

    lines.append(
        f"Crawl Status: {status} | Pages: {completed}/{total} | "
        f"Credits: {credits_used}"
    )
    if crawl_id:
        lines.append(f"Crawl ID: {crawl_id}")
    lines.append("")

    # Page results
    pages = data.get("data", [])
    if pages:
        for idx, page in enumerate(pages, 1):
            lines.append(_format_page(page, idx))
            lines.append("")

    return join_lines(lines, "")


def _format_page(page: dict, idx: int) -> str:
    """Format a single crawled page."""
    lines: list[str] = []

    metadata = page.get("metadata", {})
    title = metadata.get("title", "")
    source_url = metadata.get("sourceURL", "")
    status_code = metadata.get("statusCode", "")

    lines.append(f"--- Page {idx} ---")
    append_if(lines, "URL", source_url, indent="")
    append_if(lines, "Title", title, indent="")
    append_if(lines, "Status", status_code, indent="")
    lines.append("")

    # Content
    markdown = page.get("markdown")
    if markdown:
        lines.append(markdown)
    else:
        html = page.get("html")
        if html:
            lines.append("[HTML content available]")

    return "\n".join(lines)
