"""Tests for retry counter module."""

from mcp_server_metasearch.retry import clear_retry, get_retry_count, increment_retry


def test_retry_count_starts_at_zero():
    """Retry counter should start at 0 after clearing."""
    clear_retry()
    assert get_retry_count() == 0


def test_increment_retry():
    """Increment should increase counter and return new value."""
    clear_retry()
    assert increment_retry() == 1
    assert increment_retry() == 2
    assert get_retry_count() == 2


def test_clear_retry():
    """Clear should reset counter to 0."""
    increment_retry()
    clear_retry()
    assert get_retry_count() == 0


def test_retry_persists_across_calls():
    """Counter should persist across multiple function calls."""
    clear_retry()
    increment_retry()
    increment_retry()
    # Simulate a new process reading the same file
    assert get_retry_count() == 2
    clear_retry()
