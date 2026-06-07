"""Tests for MCP server entry point."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_metasearch.server import main


@pytest.fixture
def mock_mcp():
    return MagicMock()


def test_main_success(mock_mcp):
    """Successful startup should clear retry, log tools, and run MCP."""
    tool = MagicMock()
    tool.name = "test_tool"
    diagnostics = [MagicMock()]

    with patch("mcp_server_metasearch.server.FastMCP", return_value=mock_mcp):
        with patch("mcp_server_metasearch.server.load_environment") as mock_load:
            with patch(
                "mcp_server_metasearch.server.register_tools",
                return_value=([tool], diagnostics),
            ) as mock_register:
                with patch("mcp_server_metasearch.server.clear_retry") as mock_clear:
                    with patch("mcp_server_metasearch.server.logger") as mock_logger:
                        main()

    mock_load.assert_called_once()
    mock_register.assert_called_once_with(mock_mcp)
    mock_clear.assert_called_once()
    mock_mcp.run.assert_called_once_with(transport="stdio")
    mock_logger.info.assert_any_call(
        "Metasearch MCP server started with 1 tool(s)"
    )
    mock_logger.info.assert_any_call("  - test_tool")


def test_main_no_tools_registered(mock_mcp):
    """No tools registered should increment retry, print diagnostics, and exit."""
    diagnostics = [MagicMock()]

    with patch("mcp_server_metasearch.server.FastMCP", return_value=mock_mcp):
        with patch(
            "mcp_server_metasearch.server.register_tools",
            return_value=([], diagnostics),
        ):
            with patch(
                "mcp_server_metasearch.server.get_retry_count", return_value=1
            ):
                with patch(
                    "mcp_server_metasearch.server.increment_retry",
                    return_value=2,
                ) as mock_incr:
                    with patch(
                        "mcp_server_metasearch.server.print_diagnostics"
                    ) as mock_diag:
                        with pytest.raises(SystemExit) as exc_info:
                            main()

    assert exc_info.value.code == 1
    mock_incr.assert_called_once()
    mock_diag.assert_called_once_with(diagnostics, 2)
    mock_mcp.run.assert_not_called()


def test_main_no_tools_give_up(mock_mcp):
    """Retry count > 3 should clear retry and log give-up message."""
    diagnostics = []

    with patch("mcp_server_metasearch.server.FastMCP", return_value=mock_mcp):
        with patch(
            "mcp_server_metasearch.server.register_tools",
            return_value=([], diagnostics),
        ):
            with patch(
                "mcp_server_metasearch.server.get_retry_count", return_value=3
            ):
                with patch(
                    "mcp_server_metasearch.server.increment_retry",
                    return_value=4,
                ) as mock_incr:
                    with patch(
                        "mcp_server_metasearch.server.clear_retry"
                    ) as mock_clear:
                        with patch(
                            "mcp_server_metasearch.server.logger"
                        ) as mock_logger:
                            with pytest.raises(SystemExit) as exc_info:
                                main()

    assert exc_info.value.code == 1
    mock_incr.assert_called_once()
    mock_clear.assert_called_once()
    mock_logger.error.assert_called_once_with(
        "Startup failed after 3 retries. Giving up."
    )


def test_main_register_tools_exception(mock_mcp):
    """Exception during tool registration should be caught and exit."""
    with patch("mcp_server_metasearch.server.FastMCP", return_value=mock_mcp):
        with patch(
            "mcp_server_metasearch.server.register_tools",
            side_effect=RuntimeError("boom"),
        ):
            with patch(
                "mcp_server_metasearch.server.increment_retry",
                return_value=1,
            ) as mock_incr:
                with patch(
                    "mcp_server_metasearch.server.print_diagnostics"
                ) as mock_diag:
                    with patch(
                        "mcp_server_metasearch.server.logger"
                    ) as mock_logger:
                        with pytest.raises(SystemExit) as exc_info:
                            main()

    assert exc_info.value.code == 1
    mock_logger.exception.assert_called_once_with(
        "Failed during tool registration"
    )
    mock_incr.assert_called_once()
    mock_diag.assert_called_once_with([], 1)
    mock_mcp.run.assert_not_called()
