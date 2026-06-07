"""mcp-server-metasearch package."""

try:
    from importlib.metadata import version

    __version__ = version("mcp-server-metasearch")
except ImportError:  # pragma: no cover
    __version__ = "unknown"
