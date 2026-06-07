# MCP Server Metasearch

[![CI](https://github.com/busigui2023/mcp-server-metasearch/actions/workflows/ci.yml/badge.svg)](https://github.com/busigui2023/mcp-server-metasearch/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-metasearch)](https://pypi.org/project/mcp-server-metasearch/)

**English** | [简体中文](README.zh.md)

A local MCP (Model Context Protocol) server that aggregates **15 web search and extraction tools** across 5 providers (Jina, Tavily, Exa, Firecrawl, Bocha) behind a unified interface. Each tool is gated by both an on/off switch and an API key check — AI agents only see tools they can actually use.

**Status**: v0.2.6 — Production-ready with full test coverage (123 tests, 91% coverage).

## Why MCP Server Metasearch?

Instead of configuring 5 separate MCP servers (one per provider), metasearch gives you a **single unified interface** with:

- **Zero-config tool exposure** — only tools with valid API keys are visible to AI agents
- **Plugin architecture** — add a new provider by dropping one Python file, no framework changes
- **Shared infrastructure** — connection pooling, response caching, and startup diagnostics out of the box

## Table of Contents

- [Quick Start](#quick-start)
- [Core Features](#core-features)
- [Deployment Guide](#deployment-guide)
  - [Claude Code](#claude-code)
  - [OpenClaw](#openclaw)
  - [Hermes Agent](#hermes-agent)
- [Built-in Tools](#built-in-tools)
- [Configuration Reference](#configuration-reference)
- [Adding New Tools](#adding-new-tools)
- [Troubleshooting FAQ](#troubleshooting-faq)
- [Development & Testing](#development--testing)

## Quick Start

### Install from PyPI

```bash
pip install mcp-server-metasearch
```

### Or install from source

```bash
git clone https://github.com/busigui2023/mcp-server-metasearch.git
cd mcp-server-metasearch
uv venv && uv pip install -e ".[dev]"
```

### Configure

```bash
mkdir -p ~/.config/mcp-server-metasearch
cp .env.example ~/.config/mcp-server-metasearch/.env
# Edit ~/.config/mcp-server-metasearch/.env with your API keys
```

### Run

```bash
mcp-server-metasearch
```

Or connect via any MCP client — see [Deployment Guide](#deployment-guide) below.

## Core Features

- **Plugin architecture**: Add or remove web tools by dropping a single Python file. No framework code changes.
- **Dual validation**: Every tool requires both `TOOL_*_ENABLED=true` and the presence of its API key(s) to be exposed.
- **Key-optional support**: Some tools may work without an API key; others strictly require one.
- **Startup resilience**: If zero tools are available, the server fails with a detailed diagnostic report and retries up to 3 times before giving up.
- **Local logging**: All runtime logs write to both stderr (safe for stdio transport) and `logs/mcp-server-metasearch.log`.
- **Connection pool reuse**: Shared `httpx.AsyncClient` across all tools eliminates per-request connection overhead, with graceful shutdown via `atexit`.
- **Response caching**: In-memory TTL cache (600s) with registry-level wrapping — zero tool code changes.
- **Optimized config loading**: Environment file is read only once per process lifetime, avoiding repeated disk I/O on every tool call.
- **Clean protocol handshake**: The server does not advertise unused `resources` or `prompts` capabilities. This prevents MCP clients (e.g. Hermes) from auto-generating utility stubs for features this server does not implement, keeping the agent's tool list focused on the 15 actual search tools.

## Deployment Guide

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) installed (or `pip install mcp-server-metasearch`)
- API keys for the services you want to enable

### 1. Install & Configure

See [Quick Start](#quick-start) above, then continue with your MCP client setup.

### 2. Connect to an MCP Client

#### Claude Code

Claude Code reads MCP server definitions from `~/.claude/settings.json` (global) or `.claude/settings.json` inside your project directory.

**Option A — CLI wizard:**

```bash
claude mcp add metasearch -- uv run --directory /absolute/path/to/mcp-server-metasearch mcp-server-metasearch
```

**Option B — Edit config file directly:**

```json
{
  "mcpServers": {
    "metasearch": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/mcp-server-metasearch",
        "mcp-server-metasearch"
      ]
    }
  }
}
```

> **Note**: The project defines an entry point `mcp-server-metasearch` in `pyproject.toml`, so you can call it directly without `python -m`. Using `--directory` instead of `--project` ensures the working directory is set correctly, avoiding PYTHONPATH issues.

Restart Claude Code (`/quit` then re-enter). Run `/mcp` to verify the server appears.

#### OpenClaw

OpenClaw manages MCP servers through its client-side registry. Use the CLI or edit `openclaw.json` directly.

**Via CLI:**

```bash
openclaw mcp add metasearch \
  --command uv \
  --arg run \
  --arg --directory \
  --arg /absolute/path/to/mcp-server-metasearch \
  --arg mcp-server-metasearch
```

**Via JSON config (`openclaw.json` or equivalent):**

```json
{
  "mcp": {
    "servers": {
      "metasearch": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/absolute/path/to/mcp-server-metasearch",
          "mcp-server-metasearch"
        ],
        "transport": "stdio"
      }
    }
  }
}
```

Run `openclaw mcp probe metasearch` to test the connection without starting a full agent turn.

#### Hermes Agent

Hermes reads MCP servers from `~/.hermes/config.yaml` under the `mcp_servers` key.

```yaml
mcp_servers:
  metasearch:
    command: "uv"
    args:
      - "run"
      - "--directory"
      - "/absolute/path/to/mcp-server-metasearch"
      - "mcp-server-metasearch"
```

Restart Hermes or run `hermes mcp list` to verify. Use `hermes mcp test metasearch` to check connectivity and tool discovery.

#### Manual Test

```bash
uv run --directory /absolute/path/to/mcp-server-metasearch mcp-server-metasearch
```

If no tools are enabled, you will see a diagnostic table and the process exits with code 1. Fix your `.env` and retry.

## Troubleshooting FAQ

### Q: The diagnostic table shows all tools as "Skipped (switch disabled)" even though I set them to true.

**A:** The `.env` file must live at `~/.config/mcp-server-metasearch/.env`, not in the project root. The server does **not** read a local `.env` file inside the repository. Double-check the path and ensure there are no trailing spaces after `true`.

### Q: The diagnostic table shows "Skipped (missing API key)" but I added the key.

**A:** Check for these common mistakes:
- The key value is empty after the `=` sign.
- There is a `#` comment on the same line that truncates the value.
- The key name is misspelled (e.g. `JINA_APIKEY` instead of `JINA_API_KEY`).
- The `.env` file was saved with Windows line endings (`\r\n`) in a way that breaks parsing.

### Q: The MCP client says "MCP server metasearch failed to start" or the process exits immediately.

**A:** This usually means zero tools passed validation and the server exited with code 1. Check the client logs (stderr) for the diagnostic table. If you see retry messages (`Retry 1/3`, `Retry 2/3`), the server is working as designed — fix your `.env` before the 3rd retry or the client may stop trying.

### Q: I enabled some tools but the client only shows a subset of them.

**A:** Each tool is validated independently. The missing tools likely failed their own key or switch check. Look at the startup diagnostics — the table lists every tool and the exact reason it was skipped. Common cases:
- `JINA_API_KEY` missing → all jina tools hidden
- `TAVILY_API_KEY` missing → all tavily tools hidden
- A tool's switch set to `false` → that single tool hidden

Since jina tools share the same key, they appear or hide together. Tavily tools also share the same key.

### Q: `uv run mcp-server-metasearch` works manually but fails when launched by the MCP client.

**A:** MCP clients often launch the server with a different working directory or environment. Ensure:
- You use `--directory /absolute/path/to/mcp-server-metasearch` so `uv` can find `pyproject.toml` and set the correct working directory.
- The `.env` path `~/.config/mcp-server-metasearch/.env` uses the **absolute home directory** and does not depend on the working directory.

### Q: How do I completely reset the startup retry counter?

**A:** Delete the retry file:

```bash
rm ~/.cache/mcp-server-metasearch/startup_retries
```

This is useful when testing configuration changes and you want a fresh start.

### Q: Where do I find logs when the server is launched by a client?

**A:** Logs are written to **stderr** (safe for stdio transport) and also persisted to:

```
logs/mcp-server-metasearch.log
```

If the client captures stderr, look there. If not, check the log file in the project directory. Note: the log file is created relative to the server's working directory, so if the client changes CWD, the log may appear in an unexpected location.

### Q: Can I run the server without `uv`?

**A:** Yes, but you must ensure the Python environment has all dependencies installed (`mcp`, `httpx`, `pydantic-settings`). The server entry point is `python -m mcp_server_metasearch`. Using `uv` is recommended because it guarantees the correct virtual environment and dependency versions.

## Built-in Tools

**Current total: 15 tools across 5 providers.**

Not sure which tool to use? Here's the decision matrix:

| Goal | Recommended Tool | Why |
|------|-----------------|-----|
| Read a known URL / PDF | `jina_reader`, `exa_contents`, or `firecrawl_scrape` | Direct extraction, clean markdown. Firecrawl supports HTML/links output too |
| General web search | `exa_search`, `tavily_search`, `firecrawl_search`, or `bocha_web_search` | Token-efficient, rich filters. Firecrawl adds image/news search. Bocha: Chinese-optimized, domestic network |
| Company / people lookup | `exa_search` with `category` | Exa's indexed categories (50M+ companies, 1B+ people) |
| Academic papers | `exa_search` with `category="research paper"` or `firecrawl_search` with `categories=["research"]` | 100M+ papers indexed |
| Quick fact-check Q&A | `exa_answer` or `bocha_ai_search` with `answer=True` | Direct answer + citations. Bocha AI Search returns modal cards + AI summary |
| Batch URL extraction | `tavily_extract` or `firecrawl_map` + selective scrape | Tavily: up to 20 URLs. Firecrawl map: discover all site URLs, then scrape what you need |
| Deep research report | `tavily_research` | Async multi-step synthesis with citations |
| Fastest possible search | `exa_search` with `type="instant"` | ~250ms latency |
| Website URL discovery | `firecrawl_map` | 1 credit to map an entire site structure |
| Recursive site crawl | `firecrawl_crawl` | Auto-discover and scrape all subpages. Default 10-page limit for safety |
| GitHub code search | `firecrawl_search` with `categories=["github"]` | Search repos, issues, code docs |
| Chinese content / domestic network | `bocha_web_search` or `bocha_ai_search` | DeepSeek official search supplier, China-optimized, no proxy needed |

### `jina_reader`

Fetch and extract clean, LLM-friendly content from any webpage, PDF, or document URL using [jina.ai Reader](https://r.jina.ai/).

**When to use**: The AI needs to read a specific URL, parse a PDF link, or extract article content from a JS-heavy site.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | Target webpage or PDF URL. |
| `return_format` | `str` | `"markdown"` | Output format. `"markdown"`, `"text"`, or `"html"`. |
| `target_selector` | `str \| None` | `None` | CSS selector to extract only matching elements (e.g. `article.main-content`). |
| `remove_selectors` | `str \| None` | `None` | Comma-separated CSS selectors to remove (e.g. `nav, footer, .ads`). |
| `timeout` | `int` | `30` | Page load timeout in seconds (1–180). |

**API requirement**: `JINA_API_KEY` is required.

**Example flow**:
1. AI receives a user question about a blog post.
2. AI calls `jina_reader` with the blog URL.
3. Server requests `https://r.jina.ai/http://<url>` and returns clean Markdown.

---

### `jina_search`

Search the web using [jina.ai Search](https://s.jina.ai/) and retrieve LLM-friendly results with full page summaries.

**When to use**: The AI needs current web information, fact-checking, or multi-source summaries.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search keywords or natural-language question. |
| `num_results` | `int` | `5` | Number of results to return (1–20). |
| `site` | `str \| None` | `None` | Restrict search to a specific domain (e.g. `reddit.com`). |
| `search_type` | `str` | `"web"` | `"web"`, `"news"`, or `"images"`. |
| `return_format` | `str` | `"markdown"` | Result format. `"markdown"`, `"text"`, or `"html"`. |

**API requirement**: `JINA_API_KEY` is required.

**Example flow**:
1. User asks "What are the latest Python 3.14 features?"
2. AI calls `jina_search` with `query="Python 3.14 new features"`.
3. Server returns up to 5 results, each with title, URL, and full content summary.

---

### `jina_deepsearch`

Perform multi-step research on a complex topic using [jina.ai DeepSearch](https://deepsearch.jina.ai/). Combines web search, page reading, and reasoning into a single comprehensive answer with cited sources.

**When to use**: The question is broad or exploratory (e.g. "Compare vector databases for RAG in 2026"). DeepSearch autonomously searches multiple sources, reads them, and synthesizes a report.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | The research question or topic. Be specific for best results. |
| `max_tokens` | `int` | `4096` | Maximum tokens in the response. |

**API requirement**: `JINA_API_KEY` is required.

**Example flow**:
1. User asks "What are the trade-offs between Weaviate, Qdrant, and Milvus for production RAG?"
2. AI calls `jina_deepsearch` with the full question.
3. Server sends the query to `https://deepsearch.jina.ai/v1/chat/completions`.
4. Response is a structured research report with inline citations.

---

### `tavily_search`

Search the web using [Tavily](https://tavily.com/) with fine-grained filters, relevance scoring, and optional AI-generated answers.

**When to use**: You need precise search with time-range filters, domain restrictions, country boosting, or an AI-generated summary answer.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search keywords or natural-language question. |
| `search_depth` | `str` | `"basic"` | `"basic"`, `"fast"`, `"advanced"` (2 credits), or `"ultra-fast"`. |
| `max_results` | `int` | `5` | Number of results to return (0–20). |
| `topic` | `str` | `"general"` | `"general"`, `"news"`, or `"finance"`. |
| `time_range` | `str \| None` | `None` | `"day"`, `"week"`, `"month"`, or `"year"`. |
| `include_answer` | `bool` | `False` | Include an LLM-generated answer to the query. |
| `include_raw_content` | `bool` | `False` | Include full cleaned page content per result. |
| `include_images` | `bool` | `False` | Include images from search results. |
| `include_favicon` | `bool` | `False` | Include favicon URLs per result. |
| `include_domains` | `list[str] \| None` | `None` | Domains to restrict results to (max 300). |
| `exclude_domains` | `list[str] \| None` | `None` | Domains to exclude from results (max 150). |

**API requirement**: `TAVILY_API_KEY` is required. 1,000 free credits/month.

**Example flow**:
1. User asks "What happened in AI this week?"
2. AI calls `tavily_search` with `query="AI news"`, `topic="news"`, `time_range="week"`, `include_answer=true`.
3. Server returns ranked results plus a concise AI-generated answer.

---

### `tavily_extract`

Extract clean, LLM-friendly content from one or more URLs using [Tavily Extract](https://tavily.com/). Supports batch extraction and query-guided chunk reranking.

**When to use**: You already know the URLs and want to extract their content in bulk, or you want query-relevant chunks instead of full pages.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | `str \| list[str]` | — | Single URL or list of URLs to extract. |
| `query` | `str \| None` | `None` | User intent for reranking chunks. |
| `extract_depth` | `str` | `"basic"` | `"basic"` or `"advanced"` (tables, embedded content). |
| `return_format` | `str` | `"markdown"` | `"markdown"` or `"text"`. |

**API requirement**: `TAVILY_API_KEY` is required.

**Example flow**:
1. AI finds 3 relevant URLs from a prior search.
2. AI calls `tavily_extract` with `urls=[url1, url2, url3]`.
3. Server returns clean markdown for all three pages.

---

### `tavily_research`

Perform comprehensive, multi-step research using [Tavily Research](https://tavily.com/). Conducts multiple searches, analyzes sources, and generates a cited research report.

**When to use**: The question is broad and requires a synthesized report with citations (e.g. "Compare cloud providers for ML workloads in 2026"). Higher credit consumption than search.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | `str` | — | The research task or question to investigate. |
| `model` | `str` | `"auto"` | `"mini"`, `"pro"`, or `"auto"` (default). |
| `citation_format` | `str` | `"numbered"` | `"numbered"`, `"mla"`, `"apa"`, or `"chicago"`. |

**API requirement**: `TAVILY_API_KEY` is required. Research consumes significantly more credits than a single search because it runs multiple internal search + extract + synthesis steps.

**Example flow**:
1. User asks "What are the trade-offs between Weaviate, Qdrant, and Milvus for production RAG?"
2. AI calls `tavily_research` with the full question.
3. Server submits an async research task and polls until completion.
4. Response is a structured research report with numbered citations and a source list.

---

### `exa_search`

Search the web using [Exa](https://exa.ai/), a search engine optimized for LLMs. Returns highly relevant excerpts (highlights) by default for 10x token efficiency. Supports category filters and deep-reasoning modes.

**When to use**: You need token-efficient search results, company/people/research-paper category filtering, or the fastest search latency (`instant` ~250ms).

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Natural language search query. |
| `type` | `str` | `"auto"` | `"auto"`, `"fast"`, `"instant"`, `"deep-lite"`, `"deep"`, `"deep-reasoning"`. |
| `num_results` | `int` | `10` | Number of results (1–100). |
| `category` | `str \| None` | `None` | `"company"`, `"people"`, `"research paper"`, `"news"`, `"personal site"`, `"financial report"`. |
| `content_mode` | `str` | `"highlights"` | `"highlights"` (default), `"text"`, or `"summary"`. |
| `include_domains` | `list[str] \| None` | `None` | Whitelist domains (max 1200). |
| `exclude_domains` | `list[str] \| None` | `None` | Blacklist domains (max 1200). Not supported with `company`/`people`. |
| `max_age_hours` | `int \| None` | `None` | `0`=always livecrawl, `-1`=cache only. |

**API requirement**: `EXA_API_KEY` is required.

**Example flow**:
1. User asks "Find Series A agtech companies in the US."
2. AI calls `exa_search` with `query="agtech companies US Series A"`, `category="company"`, `content_mode="highlights"`.
3. Server returns up to 10 company pages with key excerpts.

---

### `exa_contents`

Extract clean, LLM-ready content from one or more URLs using [Exa Contents](https://exa.ai/). Handles JS-rendered pages, PDFs, and complex layouts. Supports subpage crawling.

**When to use**: You already know the URLs and want to extract their content, optionally crawling linked subpages.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | `str \| list[str]` | — | Single URL or list of URLs. |
| `content_mode` | `str` | `"text"` | `"text"` (full page), `"highlights"`, or `"summary"`. |
| `max_age_hours` | `int \| None` | `None` | Content freshness control. |
| `subpages` | `int` | `0` | Number of subpages to crawl per URL. |
| `subpage_target` | `list[str] \| None` | `None` | Keywords to prioritize subpages. |

**API requirement**: `EXA_API_KEY` is required.

**Example flow**:
1. AI finds a relevant documentation URL.
2. AI calls `exa_contents` with `urls="https://docs.example.com"`, `subpages=10`, `subpage_target=["api", "reference"]`.
3. Server returns content from the root page plus up to 10 linked subpages.

---

### `exa_answer`

Get a direct LLM answer to a question informed by [Exa](https://exa.ai/) search results. Ideal for quick factual lookups.

**When to use**: You need a concise answer to a specific question, not a list of search results.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | The question to answer. |
| `text` | `bool` | `False` | Include full source text in citations. |

**API requirement**: `EXA_API_KEY` is required.

**Example flow**:
1. User asks "What is SpaceX's latest valuation?"
2. AI calls `exa_answer` with the question.
3. Server returns "$350 billion" plus cited sources.

---

### `firecrawl_scrape`

Extract clean, LLM-ready content from any webpage using [Firecrawl](https://firecrawl.dev). Supports multiple output formats and dynamic content rendering.

**When to use**: The AI needs precise content from a known URL, especially JS-rendered sites, or wants HTML/links in addition to markdown.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | Target webpage or PDF URL. |
| `formats` | `list[str]` | `["markdown"]` | Output formats: `"markdown"`, `"html"`, `"links"`. |
| `only_main_content` | `bool` | `True` | Exclude navigation, ads, footers. |
| `timeout` | `int` | `30000` | Page load timeout in milliseconds. |
| `wait_for` | `int` | `0` | Wait time for dynamic content (ms). |

**API requirement**: `FIRECRAWL_API_KEY` is required.

---

### `firecrawl_search`

Search the web using Firecrawl and get structured content from results. Supports web, news, and image search with specialized category filtering.

**When to use**: The AI needs to search with image results, news results, or filter by GitHub/research-paper/PDF categories.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Natural language search query. |
| `limit` | `int` | `5` | Results per source type (1–50). |
| `sources` | `list[str]` | `["web"]` | Result types: `"web"`, `"news"`, `"images"`. |
| `categories` | `list[str]` | `None` | Filters: `"github"`, `"research"`, `"pdf"`. |
| `include_domains` | `list[str]` | `None` | Restrict to these domains. |
| `exclude_domains` | `list[str]` | `None` | Exclude these domains. |
| `scrape_content` | `bool` | `False` | Fetch full markdown per result (extra credits). |

**API requirement**: `FIRECRAWL_API_KEY` is required.

**Cost note**: 2 credits per 10 search results. `scrape_content=True` adds 1 credit per result page.

---

### `firecrawl_map`

Discover all URLs on a website quickly. Returns a complete link list with titles and descriptions.

**When to use**: The AI wants to explore a site's structure before deciding which pages to read, or needs to find specific pages on a large site.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | Website to map. |
| `limit` | `int` | `100` | Maximum URLs to return (1–10,000). |
| `search` | `str` | `None` | Keyword filter within the site. |

**API requirement**: `FIRECRAWL_API_KEY` is required.

**Cost note**: Always 1 credit per call, regardless of URL count.

---

### `firecrawl_crawl`

Recursively crawl a website, discovering and scraping all reachable subpages automatically.

**When to use**: The AI needs to ingest an entire documentation site, blog, or any multi-page resource.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | — | Starting URL to crawl from. |
| `limit` | `int` | `10` | Max pages to crawl (1–100). **Default is conservative** to control credit usage. |
| `max_discovery_depth` | `int` | `None` | Max link-hops from start URL. `None` = unlimited. |
| `include_paths` | `list[str]` | `None` | Regex patterns for paths to include. |
| `exclude_paths` | `list[str]` | `None` | Regex patterns for paths to exclude. |
| `allow_subdomains` | `bool` | `False` | Follow links to subdomains. |
| `formats` | `list[str]` | `["markdown"]` | Output format per page. |

**API requirement**: `FIRECRAWL_API_KEY` is required.

**Cost note**: 1 credit per page crawled. Default `limit=10` = max 10 credits.

---

### `bocha_web_search`

Search the web using [Bocha AI](https://www.bochaai.com/), a China-optimized search engine powering DeepSeek's web search. Returns clean, structured results with webpage titles, URLs, snippets, site info, and optional AI summaries.

**When to use**: The AI needs to search Chinese content, access domestic websites, or needs a search tool that works reliably without proxy.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Natural language search query. |
| `count` | `int` | `5` | Number of results (1–50). |
| `freshness` | `str` | `None` | Time filter: `oneDay`, `oneWeek`, `oneMonth`, `oneYear`, `noLimit`, or `YYYY-MM-DD..YYYY-MM-DD`. |
| `summary` | `bool` | `False` | Include AI-generated summary per result. |
| `include_domains` | `list[str]` | `None` | Only return results from these domains. |
| `exclude_domains` | `list[str]` | `None` | Exclude results from these domains. |

**API requirement**: `BOCHA_API_KEY` is required.

**Cost note**: ¥0.036 per call. Free tier available for personal use.

---

### `bocha_ai_search`

Advanced AI-powered search using Bocha AI. Returns web results plus structured modal cards (weather, encyclopedia, stock, train schedules, medical info, etc.) and optional AI-generated answers with follow-up questions.

**When to use**: The AI needs structured data extraction (e.g., "What's the weather in Beijing?", "Stock price of Alibaba"), or wants an AI-generated summary answer alongside search results.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Natural language search query. |
| `count` | `int` | `5` | Number of web results (1–50). |
| `freshness` | `str` | `None` | Time filter (same as web search). |
| `answer` | `bool` | `False` | Include AI-generated summary answer and follow-up questions. |

**API requirement**: `BOCHA_API_KEY` is required.

**Cost note**: ¥0.060 per call. Returns modal cards + AI answer when `answer=True`.

---

## Configuration Reference

### `.env` Full Example

```bash
# ── Jina AI ──
JINA_API_KEY=jina_xxxxxxxxxxxxxxxxxxxxxxxx
TOOL_JINA_READER_ENABLED=true
TOOL_JINA_SEARCH_ENABLED=true
TOOL_JINA_DEEPSEARCH_ENABLED=true

# ── Tavily ──
# TAVILY_API_KEY=tvly-xxxxxxxx
# TOOL_TAVILY_SEARCH_ENABLED=true
# TOOL_TAVILY_EXTRACT_ENABLED=true
# TOOL_TAVILY_RESEARCH_ENABLED=true

# ── Exa ──
# EXA_API_KEY=your_exa_api_key_here
# TOOL_EXA_SEARCH_ENABLED=true
# TOOL_EXA_CONTENTS_ENABLED=true
# TOOL_EXA_ANSWER_ENABLED=true

# ── Firecrawl ──
# FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxx
# TOOL_FIRECRAWL_SCRAPE_ENABLED=true
# TOOL_FIRECRAWL_SEARCH_ENABLED=true
# TOOL_FIRECRAWL_MAP_ENABLED=true
# TOOL_FIRECRAWL_CRAWL_ENABLED=true

# ── 博查 Bocha AI ──
# BOCHA_API_KEY=sk-xxxxxxxxxxxxxxxx
# TOOL_BOCHA_WEB_SEARCH_ENABLED=true
# TOOL_BOCHA_AI_SEARCH_ENABLED=true

```

### How Dual Validation Works

For every discovered tool, the server checks two conditions at startup:

1. **Switch check**: `TOOL_<NAME>_ENABLED` must be `true`.
2. **Key check**: All `required_env_vars` must be present and non-empty in `.env`.

Both must pass for the tool to be registered. If a tool fails either check, it appears in the startup diagnostic table with the exact reason.

## Development & Testing

### Run Tests

```bash
uv run pytest tests/ -v
```

### View Logs

Runtime logs are written to:

- **stderr** (MCP-safe, visible in client consoles)
- **`logs/mcp-server-metasearch.log`** (rotated at 5 MB, 3 backups kept)

```bash
tail -f logs/mcp-server-metasearch.log
```

### Startup Diagnostics

If no tools are registered, the server prints a diagnostic table to stderr:

```
[MCP-Metasearch] STARTUP DIAGNOSTICS
┌────────────────────┬─────────┬─────────────────┬─────────────────────────────┐
│ Tool               │ Switch  │ API Key         │ Result                      │
├────────────────────┼─────────┼─────────────────┼─────────────────────────────┤
│ jina_reader        │ OFF     │ JINA_API_KEY    │ Skipped (switch disabled)   │
│ jina_search        │ ON      │ MISSING         │ Skipped (missing API key)   │
└────────────────────┴─────────┴─────────────────┴─────────────────────────────┘
```

## Adding New Tools

1. Create `src/mcp_server_metasearch/tools/my_tool.py`.
2. Inherit from `BaseTool`:

```python
from mcp_server_metasearch.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "What this tool does."
    required_env_vars = ["MY_API_KEY"]   # or [] if no key needed
    enabled_env_var = "TOOL_MY_TOOL_ENABLED"

    async def call(self, param: str) -> str:
        ...
```

3. Add the key and switch to `~/.config/mcp-server-metasearch/.env`.
4. Restart the MCP client. The tool is auto-discovered — no edits to `server.py` or `tool_registry.py` needed.

## Project Structure

```
mcp-server-metasearch/
├── .env.example              # Config template
├── pyproject.toml            # Package metadata & dependencies
├── scripts/                  # E2E smoke tests per provider
├── src/mcp_server_metasearch/
│   ├── server.py             # FastMCP instance & startup flow
│   ├── tool_registry.py      # Auto-discovery, dual validation & cache wrapping
│   ├── config.py             # .env loading (single-read) & pydantic-settings
│   ├── http_client.py        # Shared httpx.AsyncClient with graceful shutdown
│   ├── cache.py              # In-memory TTL response cache
│   ├── diagnostics.py        # Startup failure reports
│   ├── retry.py              # Persistent retry counter
│   └── tools/                # One file per tool (plugin architecture)
│       ├── base.py           # BaseTool abstract class
│       ├── formatting.py     # Shared formatting utilities
│       ├── jina_*.py         # Jina AI tools (reader, search, deepsearch)
│       ├── tavily_*.py       # Tavily tools (search, extract, research)
│       ├── exa_*.py          # Exa tools (search, contents, answer)
│       ├── firecrawl_*.py    # Firecrawl tools (scrape, search, map, crawl)
│       └── bocha_*.py        # Bocha tools (web_search, ai_search)
└── tests/                    # Unit tests (123 tests, 91% coverage)
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
