"""Jina AI Reader tool."""

from typing import Literal

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.tools.base import BaseTool

# Future format extensions:
# "screenshot" - Full page screenshot
# "pageshot" - Above-the-fold screenshot
# "vlm" - VLM-generated description
# "readerlm-v2" - ReaderLM v2 output


class JinaReaderTool(BaseTool):
    name = "jina_reader"
    description = (
        "Use when reading a single webpage, PDF, or document.\n"
        "Params: url (required), return_format (\"markdown\"|\"text\"|\"html\"), target_selector (CSS filter), remove_selectors (CSS exclude), timeout (1-180s)"
    )
    required_env_vars = ["JINA_API_KEY"]
    enabled_env_var = "TOOL_JINA_READER_ENABLED"

    async def call(
        self,
        url: str,
        return_format: Literal["markdown", "text", "html"] = "markdown",
        target_selector: str | None = None,
        remove_selectors: str | None = None,
        timeout: int = 30,
    ) -> str:
        """Fetch content from a URL via jina.ai Reader.

        Args:
            url: Target webpage or PDF URL.
            return_format: Output format. "markdown" (default), "text", or "html".
            target_selector: CSS selector to extract only matching elements.
            remove_selectors: Comma-separated CSS selectors to remove before extraction.
            timeout: Page load timeout in seconds (1-180).
        """
        # Pass the original URL directly to Jina Reader
        api_url = f"https://r.jina.ai/{url}"

        settings = get_settings()
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.jina_api_key}",
            "Accept": "text/plain",
        }

        if return_format in ("text", "html"):
            headers["X-Respond-With"] = return_format
        # "markdown" is the default behavior; no extra header needed

        if target_selector:
            headers["X-Target-Selector"] = target_selector
        if remove_selectors:
            headers["X-Remove-Selector"] = remove_selectors
        if timeout != 30:
            headers["X-Timeout"] = str(max(1, min(180, timeout)))

        client = get_http_client()
        response = await client.get(api_url, headers=headers, timeout=60)
        response.raise_for_status()
        return response.text
