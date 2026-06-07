"""Shared formatting utilities for tool responses."""

from typing import Any


def join_lines(lines: list[str], default: str = "No results.") -> str:
    """Join lines with newlines, returning default if empty."""
    return "\n".join(lines) if lines else default


def append_if(lines: list[str], label: str, value: Any, indent: str = "   ") -> None:
    """Append ``{indent}{label}: {value}`` if value is present and not empty."""
    if value is not None and str(value) != "":
        lines.append(f"{indent}{label}: {value}")


def append_numbered(lines: list[str], idx: int, title: str, indent: str = "") -> None:
    """Append a numbered item header."""
    lines.append(f"{indent}{idx}. {title}")


def append_meta_line(lines: list[str], parts: list[str], indent: str = "   ") -> None:
    """Append joined metadata parts if non-empty."""
    if parts:
        lines.append(f"{indent}{' | '.join(parts)}")


def format_bocha_web_result(result: dict, idx: int, include_icon: bool = False) -> str:
    """Format a single Bocha web search result."""
    lines: list[str] = []
    name = result.get("name", "Untitled")
    url = result.get("url", "")
    snippet = result.get("snippet", "")
    summary_text = result.get("summary", "")
    site_name = result.get("siteName", "")
    date_published = result.get("datePublished", "")
    date_last_crawled = result.get("dateLastCrawled", "")

    lines.append(f"{idx}. {name}")
    append_if(lines, "URL", url)
    if snippet:
        lines.append(f"   摘要: {snippet}")
    if summary_text:
        lines.append(f"   AI摘要: {summary_text}")

    meta_parts: list[str] = []
    if site_name:
        meta_parts.append(f"站点: {site_name}")
    if include_icon:
        site_icon = result.get("siteIcon", "")
        if site_icon:
            meta_parts.append(f"图标: {site_icon}")
    if date_published:
        meta_parts.append(f"发布时间: {date_published}")
    elif date_last_crawled:
        meta_parts.append(f"抓取时间: {date_last_crawled}")

    append_meta_line(lines, meta_parts)
    return "\n".join(lines)
