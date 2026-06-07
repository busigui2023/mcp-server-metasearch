# Contributing to MCP Server Metasearch

Thank you for your interest in contributing! This document explains how to get started.

## Development Setup

```bash
git clone https://github.com/busigui2023/mcp-server-metasearch.git
cd mcp-server-metasearch
uv venv
uv pip install -e ".[dev]"
```

Run the test suite:

```bash
uv run pytest tests/ -v
```

## Adding a New Tool

The plugin architecture makes it straightforward to add new tools.

### 1. Create a tool file

Create a new file in `src/mcp_server_metasearch/tools/` (e.g. `my_provider.py`).

Your tool must:
- Inherit from `BaseTool` (imported from `mcp_server_metasearch.tools.base`)
- Implement `name`, `description`, `parameters_schema`, and `call()`
- Use `get_settings()` from `mcp_server_metasearch.config` for API key checks

See existing tools (e.g. `jina_search.py`, `exa_search.py`) for reference.

### 2. Add tool switches to `.env.example`

```bash
# ── My Provider ──
# MY_API_KEY=your_key_here
# TOOL_MY_PROVIDER_ENABLED=true
```

### 3. Write tests

Create `tests/test_my_provider.py` with unit tests covering:
- Successful API call
- HTTP error handling
- Empty/failed response formatting
- Invalid parameters

### 4. Verify

```bash
uv run pytest tests/ -v
```

### 5. Submit a PR

Follow the PR template. Ensure CI passes before requesting review.

## Code Style

- Use `ruff` for formatting (if configured)
- All public functions should have docstrings
- No hardcoded API keys or credentials
- Use `httpx.AsyncClient` from `http_client.py` for all HTTP requests (connection pool reuse)

## Reporting Issues

- Use the [Bug Report](https://github.com/busigui2023/mcp-server-metasearch/issues/new?template=bug_report.yml) template for bugs
- Use the [Feature Request](https://github.com/busigui2023/mcp-server-metasearch/issues/new?template=feature_request.yml) template for new features

## Pull Request Process

1. Fork the repo and create a branch from `master`
2. Make your changes with tests
3. Ensure all tests pass (`uv run pytest tests/ -v`)
4. Update documentation if needed
5. Submit the PR and fill out the PR template

## Questions?

Open a [Discussion](https://github.com/busigui2023/mcp-server-metasearch/discussions) or an issue.
