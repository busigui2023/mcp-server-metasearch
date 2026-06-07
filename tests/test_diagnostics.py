"""Tests for diagnostics module."""

from mcp_server_metasearch.diagnostics import ToolDiagnostic, print_diagnostics


def test_print_diagnostics(capsys):
    """Diagnostic report should contain tool info and retry count."""
    tools = [
        ToolDiagnostic(
            name="test_tool",
            switch="TOOL_TEST_ENABLED",
            switch_state="ON",
            api_key="TEST_KEY",
            api_key_state="PRESENT",
            result="Registered",
        ),
    ]
    print_diagnostics(tools, 2)
    captured = capsys.readouterr()
    err = captured.err

    assert "[MCP-Metasearch] STARTUP DIAGNOSTICS" in err
    assert "test_tool" in err
    assert "Retry attempt: 2/3" in err
    assert "Registered" in err
    assert "ACTION REQUIRED:" in err


def test_print_diagnostics_empty_tools(capsys):
    """Empty tool list should still print headers and action items."""
    print_diagnostics([], 1)
    captured = capsys.readouterr()
    err = captured.err

    assert "STARTUP DIAGNOSTICS" in err
    assert "ACTION REQUIRED:" in err
