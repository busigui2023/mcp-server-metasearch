"""MCP Server entry point."""

import logging
import logging.handlers
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    GetPromptRequest,
    ListPromptsRequest,
    ListResourcesRequest,
    ReadResourceRequest,
)

from mcp_server_metasearch.config import load_environment
from mcp_server_metasearch.diagnostics import print_diagnostics
from mcp_server_metasearch.retry import clear_retry, get_retry_count, increment_retry
from mcp_server_metasearch.tool_registry import register_tools

# Ensure logs directory exists at project root (absolute path)
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging to stderr and rotating file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.handlers.RotatingFileHandler(
            LOG_DIR / "mcp-server-metasearch.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
        ),
    ],
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    load_environment()
    mcp = FastMCP("metasearch")

    # Remove unused request handlers so capabilities().resources and
    # capabilities().prompts are None instead of empty objects.  This
    # prevents MCP clients (e.g. Hermes) from auto-generating utility
    # stubs for promps/resources that this server does not actually serve.
    for req in (
        GetPromptRequest,
        ListPromptsRequest,
        ListResourcesRequest,
        ReadResourceRequest,
    ):
        mcp._mcp_server.request_handlers.pop(req, None)

    retry_count = get_retry_count()

    try:
        registered, diagnostics = register_tools(mcp)
    except Exception:
        logger.exception("Failed during tool registration")
        retry_count = increment_retry()
        print_diagnostics([], retry_count)
        sys.exit(1)

    if not registered:
        retry_count = increment_retry()
        print_diagnostics(diagnostics, retry_count)

        if retry_count > 3:
            logger.error("Startup failed after 3 retries. Giving up.")
            clear_retry()
        else:
            logger.error(f"No tools registered. Retry {retry_count}/3.")

        sys.exit(1)

    # Success path
    clear_retry()
    logger.info(f"Metasearch MCP server started with {len(registered)} tool(s)")
    for tool in registered:
        logger.info(f"  - {tool.name}")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
