"""Tavily Research tool."""

import asyncio
from typing import Literal

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, append_numbered, join_lines

TAVILY_RESEARCH_URL = "https://api.tavily.com/research"
TAVILY_RESEARCH_STATUS_URL = "https://api.tavily.com/research"

# Polling configuration
POLL_INTERVAL_SECONDS = 3
MAX_POLL_ATTEMPTS = 60


class TavilyResearchTool(BaseTool):
    name = "tavily_research"
    description = (
        "Use when you need a comprehensive multi-angle research report with citations. Higher credit cost than search.\n"
        "Params: input (req), model (\"mini\"|\"pro\"|\"auto\"), citation_format (\"numbered\"|\"mla\"|\"apa\"|\"chicago\")"
    )
    required_env_vars = ["TAVILY_API_KEY"]
    enabled_env_var = "TOOL_TAVILY_RESEARCH_ENABLED"

    async def call(
        self,
        input: str,
        model: Literal["mini", "pro", "auto"] = "auto",
        citation_format: Literal["numbered", "mla", "apa", "chicago"] = "numbered",
    ) -> str:
        """Run comprehensive research via Tavily.

        Args:
            input: The research task or question to investigate.
            model: Research agent model. "mini" for targeted research,
                "pro" for comprehensive multi-angle research, "auto" (default).
            citation_format: Citation style. "numbered" (default), "mla",
                "apa", or "chicago".

        Returns:
            A formatted research report with citations, or status information
            if the task is still pending after max polling time.
        """
        settings = get_settings()

        payload: dict[str, object] = {
            "input": input,
            "model": model,
            "citation_format": citation_format,
        }

        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        # Step 1: Create research task
        create_response = await client.post(
            TAVILY_RESEARCH_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        create_response.raise_for_status()
        create_data = create_response.json()

        request_id = create_data.get("request_id")
        if not request_id:
            raise RuntimeError(
                f"Research task creation failed: no request_id in response. "
                f"Response: {create_data}"
            )

        # Step 2: Poll for completion
        status_data = await _poll_research_status(request_id, headers)

        return _format_research_results(status_data)


async def _poll_research_status(
    request_id: str,
    headers: dict[str, str],
) -> dict:
    """Poll Tavily research status until completed, failed, or timeout."""
    status_url = f"{TAVILY_RESEARCH_STATUS_URL}/{request_id}"

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

        if status == "completed":
            return data
        if status == "failed":
            return data

        # Still pending or in_progress — continue polling

    # Timeout: return the last known state
    return {
        "status": "timeout",
        "request_id": request_id,
        "message": (
            f"Research task is still in progress after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds. "
            f"Use request_id '{request_id}' to check status later."
        ),
    }


def _format_research_results(data: dict) -> str:
    """Format Tavily research response into human-readable text."""
    lines: list[str] = []

    status = data.get("status", "")
    request_id = data.get("request_id", "")

    if status == "timeout":
        lines.append(data.get("message", "Research task timed out."))
        return join_lines(lines, "")

    if status == "failed":
        lines.append("## Research Failed")
        lines.append(f"Request ID: {request_id}")
        return "\n".join(lines)

    if status != "completed":
        lines.append(f"## Research Status: {status}")
        lines.append(f"Request ID: {request_id}")
        return "\n".join(lines)

    # Completed
    lines.append("# Research Report")
    lines.append("")

    content = data.get("content")
    if content is not None:
        if isinstance(content, str):
            lines.append(content)
        else:
            lines.append(str(content))
        lines.append("")

    sources = data.get("sources", [])
    if sources:
        lines.append("## Sources")
        for idx, source in enumerate(sources, 1):
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            favicon = source.get("favicon")
            append_numbered(lines, idx, title)
            if url:
                lines.append(f"   {url}")
            append_if(lines, "Favicon", favicon)
            lines.append("")

    created_at = data.get("created_at")
    if created_at:
        lines.append(f"Created at: {created_at}")

    response_time = data.get("response_time")
    if response_time is not None:
        lines.append(f"Response time: {response_time}s")

    if request_id:
        lines.append(f"Request ID: {request_id}")

    return "\n".join(lines)
