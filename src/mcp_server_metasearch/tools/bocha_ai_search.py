"""Bocha AI Search tool."""

import json

from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.tools.base import BaseTool
from mcp_server_metasearch.tools.formatting import (
    format_bocha_web_result,
    join_lines,
)

BOCHA_AI_SEARCH_URL = "https://api.bochaai.com/v1/ai-search"


class BochaAiSearchTool(BaseTool):
    name = "bocha_ai_search"
    description = (
        "Use when you need structured cards (weather, stocks, encyclopedia) plus AI answers.\n"
        "Params: query (req), count (1-50, def 5), freshness (\"oneDay\"|\"oneWeek\"|\"oneMonth\"|\"oneYear\"|\"noLimit\"|\"YYYY-MM-DD..YYYY-MM-DD\"), answer (AI answer + follow-ups)"
    )
    required_env_vars = ["BOCHA_API_KEY"]
    enabled_env_var = "TOOL_BOCHA_AI_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        count: int = 5,
        freshness: str | None = None,
        answer: bool = False,
    ) -> str:
        """Perform AI-enhanced search via Bocha.

        Args:
            query: Natural language search query.
            count: Number of web results to return (1-50). Default 5.
            freshness: Time filter. "oneDay", "oneWeek", "oneMonth",
                "oneYear", "noLimit", or a custom date range
                "YYYY-MM-DD..YYYY-MM-DD".
            answer: If True, include an AI-generated summary answer and
                follow-up questions.
        """
        api_key = get_settings().bocha_api_key

        payload: dict[str, object] = {
            "query": query,
            "count": max(1, min(50, count)),
        }

        if freshness is not None:
            payload["freshness"] = freshness
        if answer:
            payload["answer"] = True

        # MCP tools do not support streaming; always disable
        payload["stream"] = False

        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = get_http_client()
        response = await client.post(
            BOCHA_AI_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        return _format_ai_search_results(data)


def _format_ai_search_results(data: dict) -> str:
    """Format Bocha AI search JSON response into human-readable text.

    AI Search returns a messages array instead of a flat data object:
    - messages[].type="source" + content_type="webpage" → web results
    - messages[].type="source" + content_type="image" → images
    - messages[].type="source" + content_type="video" → videos
    - messages[].type="answer" → AI-generated answer
    - messages[].type="follow_up" → follow-up questions
    """
    lines: list[str] = []

    code = data.get("code", 0)
    if code != 200:
        msg = data.get("msg", "Unknown error")
        lines.append(f"AI Search failed (code {code}): {msg}")
        return "\n".join(lines)

    messages = data.get("messages", [])
    if not messages:
        lines.append("No results found.")
        return "\n".join(lines)

    web_results: list[dict] = []
    images: list[dict] = []
    videos: list[dict] = []
    answer_text = ""
    follow_ups: list[str] = []

    for msg in messages:
        msg_type = msg.get("type", "")
        content_type = msg.get("content_type", "")
        content = msg.get("content", "")

        if msg_type == "source":
            if content_type == "webpage":
                parsed = _parse_json_content(content)
                if isinstance(parsed, dict):
                    web_results.extend(parsed.get("value", []))
            elif content_type == "image":
                parsed = _parse_json_content(content)
                if isinstance(parsed, dict):
                    images.extend(parsed.get("value", []))
            elif content_type == "video":
                parsed = _parse_json_content(content)
                if isinstance(parsed, dict):
                    videos.extend(parsed.get("value", []))
        elif msg_type == "answer":
            answer_text = str(content)
        elif msg_type == "follow_up":
            parsed = _parse_json_content(content)
            if isinstance(parsed, list):
                follow_ups.extend(parsed)

    # Output sections
    has_content = bool(web_results or images or videos or answer_text)
    if not has_content:
        lines.append("No results found.")
        return "\n".join(lines)

    # Images
    if images:
        lines.append(f"## 图片结果 ({len(images)})")
        lines.append("")
        for idx, img in enumerate(images, 1):
            url = img.get("contentUrl", "")
            host = img.get("hostPageUrl", "")
            lines.append(f"{idx}. {url}")
            if host:
                lines.append(f"   来源: {host}")
        lines.append("")

    # Web results
    if web_results:
        lines.append(f"## 网页结果 ({len(web_results)})")
        lines.append("")
        for idx, result in enumerate(web_results, 1):
            lines.append(format_bocha_web_result(result, idx, include_icon=False))
            lines.append("")

    # AI answer
    if answer_text:
        lines.append("---")
        lines.append("## AI 总结答案")
        lines.append("")
        lines.append(answer_text)
        lines.append("")

    # Follow-up questions
    if follow_ups:
        lines.append("## 你可能还想问")
        lines.append("")
        for q in follow_ups:
            lines.append(f"- {q}")
        lines.append("")

    return join_lines(lines, "No results found.")


def _parse_json_content(content: str) -> dict | list | None:
    """Parse JSON string content from AI Search messages."""
    if not content or not isinstance(content, str):
        return None
    try:
        parsed: dict | list = json.loads(content)
        if isinstance(parsed, (dict, list)):
            return parsed
        return None
    except json.JSONDecodeError:
        return None



