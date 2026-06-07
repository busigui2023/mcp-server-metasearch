"""Tool discovery and dynamic registration."""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_metasearch.cache import ToolResponseCache, get_cache
from mcp_server_metasearch.diagnostics import ToolDiagnostic
from mcp_server_metasearch.tools.base import BaseTool

logger = logging.getLogger(__name__)


def discover_tools() -> list[BaseTool]:
    """Scan tools/ directory and return all valid tool instances."""
    tools: list[BaseTool] = []
    tools_dir = Path(__file__).parent / "tools"

    for finder, module_name, ispkg in pkgutil.iter_modules([str(tools_dir)]):
        if module_name.startswith("_") or module_name == "base":
            continue

        try:
            module = importlib.import_module(
                f"mcp_server_metasearch.tools.{module_name}"
            )
        except Exception as e:
            logger.warning(f"Failed to import tool module {module_name}: {e}")
            continue

        # Find all BaseTool subclasses in the module
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseTool)
                and obj is not BaseTool
                and not getattr(obj, "__abstractmethods__", None)
            ):
                try:
                    instance = obj()
                    tools.append(instance)
                    logger.debug(f"Discovered tool: {instance.name}")
                except Exception as e:
                    logger.warning(f"Failed to instantiate tool {name}: {e}")

    return tools


def _wrap_with_cache(
    call_fn: Any,
    tool_name: str,
    cache: ToolResponseCache,
) -> Any:
    """Wrap a tool's call method with response caching.

    Preserves the original signature so FastMCP can generate correct
    JSON Schema for tool parameters.
    """
    sig = inspect.signature(call_fn)

    async def wrapper(*args: Any, **kwargs: Any) -> str:
        cached = cache.get(tool_name, kwargs)
        if cached is not None:
            return cached
        result = await call_fn(*args, **kwargs)
        cache.set(tool_name, kwargs, result)
        return result  # type: ignore[no-any-return]

    # Preserve metadata for FastMCP schema generation.
    wrapper.__name__ = getattr(call_fn, "__name__", "call")
    wrapper.__doc__ = getattr(call_fn, "__doc__", None)
    wrapper.__module__ = getattr(call_fn, "__module__", "") or ""
    wrapper.__qualname__ = getattr(call_fn, "__qualname__", "call")
    wrapper.__signature__ = sig  # type: ignore[attr-defined]
    wrapper.__annotations__ = {
        k: v for k, v in getattr(call_fn, "__annotations__", {}).items() if k != "self"
    }

    return wrapper


def register_tools(mcp: FastMCP) -> tuple[list[BaseTool], list[ToolDiagnostic]]:
    """Register tools with dual validation and return diagnostics."""
    from mcp_server_metasearch.config import get_settings

    settings = get_settings()
    cache = get_cache()
    discovered = discover_tools()
    registered: list[BaseTool] = []
    diagnostics: list[ToolDiagnostic] = []
    registered_names: set[str] = set()

    for tool in discovered:
        # Duplicate name check
        if tool.name in registered_names:
            logger.error(f"Duplicate tool name: {tool.name}. Skipping.")
            diagnostics.append(
                ToolDiagnostic(
                    name=tool.name,
                    switch=tool.enabled_env_var,
                    switch_state="N/A",
                    api_key="N/A",
                    api_key_state="N/A",
                    result="Skipped (duplicate name)",
                )
            )
            continue

        # Check switch
        switch_on = settings.is_tool_enabled(tool.enabled_env_var)
        switch_state = "ON" if switch_on else "OFF"

        # Check API keys
        if not tool.required_env_vars:
            api_key_state = "N/A"
            keys_present = True
            api_key_label = "(none required)"
        else:
            keys_present = all(
                settings.has_api_key(key) for key in tool.required_env_vars
            )
            api_key_state = "PRESENT" if keys_present else "MISSING"
            api_key_label = tool.required_env_vars[0]

        # Determine result
        if not switch_on:
            result = "Skipped (switch disabled)"
            should_register = False
        elif not keys_present:
            result = "Skipped (missing API key)"
            should_register = False
        else:
            result = "Registered"
            should_register = True

        diagnostics.append(
            ToolDiagnostic(
                name=tool.name,
                switch=tool.enabled_env_var,
                switch_state=switch_state,
                api_key=api_key_label,
                api_key_state=api_key_state,
                result=result,
            )
        )

        if should_register:
            try:
                wrapped_call = _wrap_with_cache(tool.call, tool.name, cache)
                mcp.add_tool(
                    wrapped_call,
                    name=tool.name,
                    description=tool.description,
                )
                registered.append(tool)
                registered_names.add(tool.name)
                logger.info(f"Registered tool: {tool.name}")
            except Exception as e:
                logger.error(f"Failed to register tool {tool.name}: {e}")
                diagnostics[-1].result = f"Failed: {e}"

    return registered, diagnostics
