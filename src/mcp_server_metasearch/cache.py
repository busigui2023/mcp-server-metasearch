"""In-memory TTL cache for tool response caching."""

import hashlib
import json
import time
from typing import Any


class ToolResponseCache:
    """Simple in-memory cache with TTL and size limit.

    Designed for short-lived MCP stdio server processes. Entries are
    evicted on TTL expiration or when max_size is reached.
    """

    def __init__(self, ttl_seconds: int = 600, max_size: int = 1000) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: dict[str, tuple[str, float]] = {}

    def _make_key(self, tool_name: str, kwargs: dict[str, Any]) -> str:
        """Deterministic cache key from tool name and call arguments."""
        canonical = json.dumps(kwargs, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return f"{tool_name}:{digest}"

    def get(self, tool_name: str, kwargs: dict[str, Any]) -> str | None:
        """Return cached value if present and not expired."""
        key = self._make_key(tool_name, kwargs)
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                return value
            del self._store[key]
        return None

    def set(self, tool_name: str, kwargs: dict[str, Any], value: str) -> None:
        """Store value with TTL. Evicts expired or oldest entries if needed."""
        key = self._make_key(tool_name, kwargs)
        if len(self._store) >= self.max_size:
            now = time.time()
            expired = [k for k, (_, exp) in self._store.items() if exp < now]
            for k in expired:
                del self._store[k]
            if len(self._store) >= self.max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest_key]
        self._store[key] = (value, time.time() + self.ttl)


_default_cache: ToolResponseCache | None = None


def get_cache() -> ToolResponseCache:
    """Return the module-level cache singleton."""
    global _default_cache
    if _default_cache is None:
        _default_cache = ToolResponseCache()
    return _default_cache
