"""Persistent retry counter for startup failures."""

from pathlib import Path

_RETRY_FILE = Path.home() / ".cache" / "mcp-server-metasearch" / "startup_retries"


def get_retry_count() -> int:
    """Read current retry count from persistent storage."""
    if not _RETRY_FILE.exists():
        return 0
    try:
        return int(_RETRY_FILE.read_text().strip())
    except (ValueError, OSError):
        return 0


def increment_retry() -> int:
    """Increment retry count and return new value."""
    count = get_retry_count() + 1
    _RETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _RETRY_FILE.write_text(str(count))
    return count


def clear_retry() -> None:
    """Clear retry counter after successful startup."""
    if _RETRY_FILE.exists():
        _RETRY_FILE.unlink()
