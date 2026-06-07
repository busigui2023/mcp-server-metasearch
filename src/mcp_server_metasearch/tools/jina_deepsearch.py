"""Jina AI DeepSearch tool."""

from mcp_server_metasearch.config import get_settings
from mcp_server_metasearch.http_client import get_http_client

from mcp_server_metasearch.tools.base import BaseTool

DEEPSEARCH_API_URL = "https://deepsearch.jina.ai/v1/chat/completions"
DEFAULT_MODEL = "jina-deepsearch-v1"


class JinaDeepSearchTool(BaseTool):
    name = "jina_deepsearch"
    description = (
        "Use when doing deep research on a complex topic with citations.\n"
        "Params: query (required), max_tokens (def 4096)"
    )
    required_env_vars = ["JINA_API_KEY"]
    enabled_env_var = "TOOL_JINA_DEEPSEARCH_ENABLED"

    async def call(
        self,
        query: str,
        max_tokens: int = 4096,
    ) -> str:
        """Run deep research via jina.ai DeepSearch.

        Args:
            query: The research question or topic. Be specific for best results.
            max_tokens: Maximum tokens in the response. Default 4096.
        """
        settings = get_settings()
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.jina_api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, object] = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "user", "content": query},
            ],
            "stream": False,
            "max_tokens": max_tokens,
        }

        client = get_http_client()
        response = await client.post(
            DEEPSEARCH_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        # Extract content from OpenAI-compatible ChatCompletion response
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected DeepSearch response structure: {exc}"
            ) from exc
