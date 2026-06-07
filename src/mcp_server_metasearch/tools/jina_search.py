"""Jina AI Search tool."""

import urllib.parse
from typing import Literal

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.tools.base import BaseTool


class JinaSearchTool(BaseTool):
    name = "jina_search"
    description = (
        "Use when searching the web for general info, news, or images.\n"
        "Params: query (required), num_results (1-20, def 5), site (domain filter), search_type (\"web\"|\"news\"|\"images\"), return_format (\"markdown\"|\"text\"|\"html\")"
    )
    required_env_vars = ["JINA_API_KEY"]
    enabled_env_var = "TOOL_JINA_SEARCH_ENABLED"

    async def call(
        self,
        query: str,
        num_results: int = 5,
        site: str | None = None,
        search_type: Literal["web", "news", "images"] = "web",
        return_format: Literal["markdown", "text", "html"] = "markdown",
    ) -> str:
        """Search the web via jina.ai Search.

        Args:
            query: Search keywords or question.
            num_results: Number of results to return (1-20). Default 5.
            site: Restrict search to a specific domain, e.g. "reddit.com".
            search_type: Type of search. "web" (default), "news", or "images".
            return_format: Output format for each result. "markdown" (default), "text", or "html".
        """
        encoded_query = urllib.parse.quote(query)
        api_url = f"https://s.jina.ai/{encoded_query}"

        params: dict[str, str | int] = {}
        if num_results != 5:
            params["num"] = max(1, min(20, num_results))
        if site:
            params["site"] = site
        if search_type in ("news", "images"):
            params["type"] = search_type

        settings = get_settings()
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.jina_api_key}",
        }

        if return_format in ("text", "html"):
            headers["X-Respond-With"] = return_format
        # "markdown" is the default behavior

        client = get_http_client()
        response = await client.get(
            api_url,
            headers=headers,
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        return response.text
