"""Diagnostic report generator for startup failures."""

import sys
from dataclasses import dataclass

from mcp_server_metasearch.config import ENV_FILE


@dataclass
class ToolDiagnostic:
    name: str
    switch: str
    switch_state: str  # "ON" or "OFF"
    api_key: str
    api_key_state: str  # "PRESENT", "MISSING", or "N/A"
    result: str


def print_diagnostics(
    tools: list[ToolDiagnostic],
    retry_count: int,
) -> None:
    """Print formatted diagnostic report to stderr."""
    lines = [
        "",
        "[MCP-Metasearch] STARTUP DIAGNOSTICS",
        "═" * 67,
        f"Environment file: {ENV_FILE}",
        f"Retry attempt: {retry_count}/3",
        "",
        "┌────────────────────┬─────────┬─────────────────┬─────────────────────────────┐",
        "│ Tool               │ Switch  │ API Key         │ Result                      │",
        "├────────────────────┼─────────┼─────────────────┼─────────────────────────────┤",
    ]

    for t in tools:
        lines.append(
            f"│ {t.name:<18} │ {t.switch_state:<7} │ {t.api_key:<15} │ {t.result:<27} │"
        )

    lines.extend([
        "└────────────────────┴─────────┴─────────────────┴─────────────────────────────┘",
        "",
        "ACTION REQUIRED:",
        f"1. Edit {ENV_FILE}",
        "2. Set TOOL_*_ENABLED=true for the tools you want",
        "3. Set the required API keys for those tools",
        "4. Restart your MCP client (Claude Desktop / Kimi Code)",
        "═" * 67,
        "",
    ])

    for line in lines:
        print(line, file=sys.stderr)
