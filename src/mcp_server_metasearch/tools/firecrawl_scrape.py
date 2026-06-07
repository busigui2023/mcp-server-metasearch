"""Firecrawl Scrape tool."""

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, join_lines

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v2/scrape"

SUPPORTED_FORMATS = ("markdown", "html", "links")


class FirecrawlScrapeTool(BaseTool):
    name = "firecrawl_scrape"
    description = (
        "Use when scraping a single page, especially JS-heavy sites.\n"
        "Params: url (req), formats (\"markdown\"|\"html\"|\"links\"), only_main_content (def True), timeout (ms, def 30000), wait_for (dynamic content wait ms, def 0)"
    )
    required_env_vars = ["FIRECRAWL_API_KEY"]
    enabled_env_var = "TOOL_FIRECRAWL_SCRAPE_ENABLED"

    async def call(
        self,
        url: str,
        formats: list[str] | None = None,
        only_main_content: bool = True,
        timeout: int = 30000,
        wait_for: int = 0,
    ) -> str:
        """Scrape a single URL via Firecrawl.

        Args:
            url: Target webpage or PDF URL.
            formats: Output formats. Supported: "markdown" (default), "html",
                "links". Multiple formats can be requested.
            only_main_content: If True (default), exclude navigation, ads,
                and other non-essential page elements.
            timeout: Page load timeout in milliseconds (default 30000).
            wait_for: Time to wait for dynamic content to load in
                milliseconds (default 0).
        """
        api_key = get_settings().firecrawl_api_key

        # Validate and normalize formats
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
            "formats": normalized_formats,
            "onlyMainContent": only_main_content,
            "timeout": max(1000, min(60000, timeout)),
        }

        if wait_for > 0:
            payload["waitFor"] = wait_for

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            FIRECRAWL_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_scrape_results(data)


def _format_scrape_results(data: dict) -> str:
    """Format Firecrawl scrape JSON response into human-readable text."""
    lines: list[str] = []

    success = data.get("success", False)
    if not success:
        lines.append("Scrape failed.")
        warning = data.get("warning")
        if warning:
            lines.append(f"Warning: {warning}")
        return "\n".join(lines)

    result_data = data.get("data", {})

    metadata = result_data.get("metadata", {})
    title = metadata.get("title", "")
    source_url = metadata.get("sourceURL", "")
    description = metadata.get("description", "")

    append_if(lines, "Title", title, indent="")
    append_if(lines, "URL", source_url, indent="")
    append_if(lines, "Description", description, indent="")
    if lines:
        lines.append("")

    # Markdown content
    markdown = result_data.get("markdown")
    if markdown:
        lines.append(markdown)
        lines.append("")

    # HTML content
    html = result_data.get("html")
    if html:
        lines.append("--- HTML ---")
        lines.append(html)
        lines.append("")

    # Links
    links = result_data.get("links")
    if links:
        lines.append("--- Links found on page ---")
        for link in links:
            lines.append(f"- {link}")
        lines.append("")

    warning = data.get("warning")
    if warning:
        lines.append(f"Warning: {warning}")

    return join_lines(lines, "No content extracted.")
