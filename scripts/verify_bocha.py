"""End-to-end validation script for Bocha tools.

Usage:
    export BOCHA_API_KEY=sk-xxxxxx
    export TOOL_BOCHA_WEB_SEARCH_ENABLED=true
    export TOOL_BOCHA_AI_SEARCH_ENABLED=true
    uv run python scripts/verify_bocha.py
"""

import asyncio
import os

os.environ.setdefault("TOOL_BOCHA_WEB_SEARCH_ENABLED", "true")
os.environ.setdefault("TOOL_BOCHA_AI_SEARCH_ENABLED", "true")

from mcp_server_metasearch.tools.bocha_web_search import BochaWebSearchTool
from mcp_server_metasearch.tools.bocha_ai_search import BochaAiSearchTool


async def verify_web_search() -> None:
    print("=" * 60)
    print("1. bocha_web_search")
    print("=" * 60)
    tool = BochaWebSearchTool()
    result = await tool.call(
        query="阿里巴巴2024年ESG报告",
        count=3,
        summary=True,
    )
    print(result[:2000])
    print("...\n")


async def verify_ai_search() -> None:
    print("=" * 60)
    print("2. bocha_ai_search")
    print("=" * 60)
    tool = BochaAiSearchTool()
    result = await tool.call(
        query="北京今天天气",
        count=3,
        answer=True,
    )
    print(result[:2500])
    print("...\n")


async def main() -> None:
    if not os.getenv("BOCHA_API_KEY"):
        print("Error: BOCHA_API_KEY not set.")
        print("Get a free key at https://open.bochaai.com")
        return

    await verify_web_search()
    await verify_ai_search()
    print("All Bocha tools verified successfully!")


if __name__ == "__main__":
    asyncio.run(main())
