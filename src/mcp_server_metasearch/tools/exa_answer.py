"""Exa Answer tool."""

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import append_if, append_numbered, join_lines

EXA_ANSWER_URL = "https://api.exa.ai/answer"


class ExaAnswerTool(BaseTool):
    name = "exa_answer"
    description = (
        "Use when you only need a direct answer, not full results.\n"
        "Params: query (req), text (include full source text, def False)"
    )
    required_env_vars = ["EXA_API_KEY"]
    enabled_env_var = "TOOL_EXA_ANSWER_ENABLED"

    async def call(
        self,
        query: str,
        text: bool = False,
    ) -> str:
        """Get an LLM answer via Exa.

        Args:
            query: The question or topic to answer.
            text: Include full page text for each cited source. Default False.
        """
        api_key = get_settings().exa_api_key or ""

        payload: dict[str, object] = {
            "query": query,
            "text": text,
        }

        headers: dict[str, str] = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            EXA_ANSWER_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_answer_results(data)


def _format_answer_results(data: dict) -> str:
    """Format Exa answer JSON response into human-readable text."""
    lines: list[str] = []

    request_id = data.get("requestId", "")
    if request_id:
        lines.append(f"Request ID: {request_id}")
        lines.append("")

    answer = data.get("answer")
    if answer is not None:
        lines.append("## Answer")
        if isinstance(answer, str):
            lines.append(answer)
        else:
            lines.append(str(answer))
        lines.append("")

    citations = data.get("citations", [])
    if citations:
        lines.append(f"## Sources ({len(citations)})")
        for idx, c in enumerate(citations, 1):
            title = c.get("title", "Untitled")
            url = c.get("url", "")
            author = c.get("author")
            published = c.get("publishedDate")
            text_content = c.get("text")

            lines.append("")
            append_numbered(lines, idx, title)
            if url:
                lines.append(f"   {url}")
            append_if(lines, "Author", author)
            append_if(lines, "Published", published)
            if text_content:
                lines.append(f"   Text: {text_content[:500]}...")

    cost = data.get("costDollars", {})
    if cost:
        lines.append("")
        lines.append(f"Cost: ${cost.get('total', 'unknown')}")

    return join_lines(lines, "No answer.")
