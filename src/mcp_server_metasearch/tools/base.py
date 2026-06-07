"""Base class for all metasearch tools."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for web tools.

    Each concrete tool must define its own:
    - name: MCP tool name exposed to clients
    - description: Human-readable description
    - required_env_vars: API key names needed (empty list if none)
    - enabled_env_var: Switch variable name in .env
    - call(**kwargs): Async execution logic with tool-specific parameters
    """

    name: str = ""
    description: str = ""
    required_env_vars: list[str] = []
    enabled_env_var: str = ""

    @abstractmethod
    async def call(self, **kwargs: Any) -> Any:
        """Execute the tool. Parameters are tool-specific."""
