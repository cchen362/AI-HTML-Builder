"""Shared utilities for document export."""

from app.services.exporters.base import ExportError


def validate_html(html_content: str) -> None:
    """Validate HTML content before export. Raises ExportError on failure."""
    if not html_content or not html_content.strip():
        raise ExportError("HTML content is empty")
    stripped = html_content.strip()
    if not stripped.startswith("<!DOCTYPE") and not stripped.startswith("<html"):
        raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")


def sanitize_title(title: str) -> str:
    """Sanitize document title for use in filenames."""
    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in title
    ).strip()

    # Replace spaces with hyphens for cleaner filenames
    safe = safe.replace(" ", "-")

    # Collapse multiple hyphens/underscores
    while "--" in safe:
        safe = safe.replace("--", "-")
    while "__" in safe:
        safe = safe.replace("__", "_")

    # Truncate to 60 chars at word boundary
    if len(safe) > 60:
        truncated = safe[:60]
        last_sep = max(truncated.rfind("-"), truncated.rfind("_"))
        if last_sep > 30:
            truncated = truncated[:last_sep]
        safe = truncated

    # Strip trailing separators
    safe = safe.strip("-_")

    return safe or "document"


def generate_filename(title: str, extension: str) -> str:
    """Generate sanitized filename for exported document."""
    return f"{sanitize_title(title)}.{extension}"
