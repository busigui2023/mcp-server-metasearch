"""Exa Contents tool."""

from typing import Literal

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, join_lines

EXA_CONTENTS_URL = "https://api.exa.ai/contents"

CONTENT_MODES = ("text", "highlights", "summary")


class ExaContentsTool(BaseTool):
    name = "exa_contents"
    description = (
        "Use when extracting URL content with freshness/subpage control.\n"
        "Params: urls (req), content_mode (\"text\"|\"highlights\"|\"summary\"), max_age_hours (0=live, -1=cache), subpages (0=off), subpage_target (keywords)"
    )
    required_env_vars = ["EXA_API_KEY"]
    enabled_env_var = "TOOL_EXA_CONTENTS_ENABLED"

    async def call(
        self,
        urls: str | list[str],
        content_mode: Literal["text", "highlights", "summary"] = "text",
        max_age_hours: int | None = None,
        subpages: int = 0,
        subpage_target: list[str] | None = None,
    ) -> str:
        """Extract content from URLs via Exa.

        Args:
            urls: A single URL or a list of URLs to extract content from.
            content_mode: What content to return. "text" (default, full page
                markdown), "highlights" (key excerpts), or "summary"
                (LLM-generated abstract).
            max_age_hours: Content freshness. 0 = always livecrawl.
                -1 = cache only. Omit for default (livecrawl as fallback).
            subpages: Number of subpages to crawl per URL. 0 = disabled.
            subpage_target: Keywords to prioritize when selecting subpages.
        """
        api_key = get_settings().exa_api_key or ""

        # Normalize urls to list for the API
        url_list = [urls] if isinstance(urls, str) else urls

        payload: dict[str, object] = {"urls": url_list}

        # Content mode is top-level on /contents (not nested under contents{})
        if content_mode == "text":
            payload["text"] = True
        elif content_mode == "highlights":
            payload["highlights"] = True
        elif content_mode == "summary":
            payload["summary"] = True

        if max_age_hours is not None:
            payload["maxAgeHours"] = max_age_hours
        if subpages > 0:
            payload["subpages"] = subpages
        if subpage_target:
            payload["subpageTarget"] = subpage_target

        headers: dict[str, str] = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            EXA_CONTENTS_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_contents_results(data)


def _format_contents_results(data: dict) -> str:
    """Format Exa contents JSON response into human-readable text."""
    lines: list[str] = []

    request_id = data.get("requestId", "")
    if request_id:
        lines.append(f"Request ID: {request_id}")
        lines.append("")

    results = data.get("results", [])
    if results:
        lines.append(f"## Extracted Content ({len(results)} URL(s))")
        for result in results:
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            author = result.get("author")
            published = result.get("publishedDate")
            favicon = result.get("favicon")

            lines.append(f"\n### {title}")
            append_if(lines, "URL", url, indent="")
            append_if(lines, "Author", author, indent="")
            append_if(lines, "Published", published, indent="")
            append_if(lines, "Favicon", favicon, indent="")

            text = result.get("text")
            if text:
                lines.append(f"\n{text}")

            highlights = result.get("highlights")
            if highlights:
                lines.append("\nHighlights:")
                for h in highlights:
                    lines.append(f"  - {h}")

            summary = result.get("summary")
            if summary:
                lines.append(f"\nSummary: {summary}")

            subpages = result.get("subpages", [])
            if subpages:
                lines.append(f"\nSubpages ({len(subpages)}):")
                for sp in subpages:
                    sp_title = sp.get("title", "Untitled")
                    sp_url = sp.get("url", "")
                    lines.append(f"  - {sp_title}")
                    if sp_url:
                        lines.append(f"    {sp_url}")

    # Per-URL statuses (errors are reported here, not as HTTP errors)
    statuses = data.get("statuses", [])
    failed = [s for s in statuses if s.get("status") == "error"]
    if failed:
        lines.append("")
        lines.append(f"## Failed URLs ({len(failed)})")
        for s in failed:
            url = s.get("id", "")
            error = s.get("error", {})
            tag = error.get("tag", "Unknown")
            lines.append(f"- {url}: {tag}")

    cost = data.get("costDollars", {})
    if cost:
        lines.append("")
        lines.append(f"Cost: ${cost.get('total', 'unknown')}")

    return join_lines(lines, "No extraction results.")
