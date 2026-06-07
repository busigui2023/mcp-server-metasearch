"""End-to-end validation script for Firecrawl tools.

Usage:
    export FIRECRAWL_API_KEY=fc-xxxxxx
    export TOOL_FIRECRAWL_SCRAPE_ENABLED=true
    export TOOL_FIRECRAWL_SEARCH_ENABLED=true
    export TOOL_FIRECRAWL_MAP_ENABLED=true
    export TOOL_FIRECRAWL_CRAWL_ENABLED=true
    uv run python scripts/verify_firecrawl.py
"""

import asyncio
import os

# Ensure env is loaded before importing project modules
os.environ.setdefault("TOOL_FIRECRAWL_SCRAPE_ENABLED", "true")
os.environ.setdefault("TOOL_FIRECRAWL_SEARCH_ENABLED", "true")
os.environ.setdefault("TOOL_FIRECRAWL_MAP_ENABLED", "true")
os.environ.setdefault("TOOL_FIRECRAWL_CRAWL_ENABLED", "true")

from mcp_server_metasearch.tools.firecrawl_scrape import FirecrawlScrapeTool
from mcp_server_metasearch.tools.firecrawl_search import FirecrawlSearchTool
from mcp_server_metasearch.tools.firecrawl_map import FirecrawlMapTool
from mcp_server_metasearch.tools.firecrawl_crawl import FirecrawlCrawlTool


async def verify_scrape() -> None:
    print("=" * 60)
    print("1. firecrawl_scrape")
    print("=" * 60)
    tool = FirecrawlScrapeTool()
    result = await tool.call(
        url="https://docs.firecrawl.dev",
        formats=["markdown"],
    )
    print(result[:2000])
    print("...\n")


async def verify_search() -> None:
    print("=" * 60)
    print("2. firecrawl_search")
    print("=" * 60)
    tool = FirecrawlSearchTool()
    result = await tool.call(
        query="firecrawl web scraping API",
        limit=3,
        sources=["web"],
    )
    print(result[:2000])
    print("...\n")


async def verify_map() -> None:
    print("=" * 60)
    print("3. firecrawl_map")
    print("=" * 60)
    tool = FirecrawlMapTool()
    result = await tool.call(
        url="https://docs.firecrawl.dev",
        limit=10,
    )
    print(result[:2000])
    print("...\n")


async def verify_crawl() -> None:
    print("=" * 60)
    print("4. firecrawl_crawl")
    print("=" * 60)
    tool = FirecrawlCrawlTool()
    result = await tool.call(
        url="https://docs.firecrawl.dev",
        limit=3,
        max_discovery_depth=1,
    )
    print(result[:3000])
    print("...\n")


async def main() -> None:
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Error: FIRECRAWL_API_KEY not set.")
        print("Get a free key at https://firecrawl.dev")
        return

    await verify_scrape()
    await verify_search()
    await verify_map()
    await verify_crawl()
    print("All Firecrawl tools verified successfully!")


if __name__ == "__main__":
    asyncio.run(main())
