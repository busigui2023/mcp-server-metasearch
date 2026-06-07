# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.6] - 2025-06-07

### Added
- 15 web search and extraction tools across 5 providers (Jina, Tavily, Exa, Firecrawl, Bocha)
- Plugin architecture for easy tool addition
- Dual validation (switch + API key) for tool exposure
- Connection pooling via shared `httpx.AsyncClient`
- Response caching with in-memory TTL cache (600s)
- Startup resilience with retry logic and diagnostic reporting
- Clean MCP protocol handshake (no unused capabilities)
- GitHub Actions CI workflow (Python 3.10-3.13)
- PyPI publish workflow (triggered on version tags)
- CONTRIBUTING.md, CHANGELOG.md, SECURITY.md, CODE_OF_CONDUCT.md
- Issue and PR templates
- Chinese README (README.zh.md)
