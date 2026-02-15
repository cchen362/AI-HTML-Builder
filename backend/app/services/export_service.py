"""Main export service coordinating all export operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from app.services.session_service import session_service
from app.services.exporters.base import ExportError, ExportOptions, ExportResult
from app.utils.html_validator import is_infographic_html

logger = structlog.get_logger()

# Exporter function type: (html_content, options) -> ExportResult
ExporterFn = Callable[[str, ExportOptions], Awaitable[ExportResult]]

# Registry populated during app lifespan
_exporters: dict[str, tuple[str, ExporterFn]] = {}


def register_exporter(format_key: str, format_name: str, fn: ExporterFn) -> None:
    """Register an export function for a format key."""
    _exporters[format_key.lower()] = (format_name, fn)
    logger.info("Registered exporter", format=format_key, name=format_name)


def _validate_html(html_content: str) -> None:
    """Validate HTML content before export."""
    if not html_content or not html_content.strip():
        raise ExportError("HTML content is empty")
    stripped = html_content.strip()
    if not stripped.startswith("<!DOCTYPE") and not stripped.startswith("<html"):
        raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")


def _sanitize_title(title: str) -> str:
    """Sanitize document title for use in filenames."""
    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in title
    ).strip()
    return safe or "document"


async def _export_html(html_content: str, options: ExportOptions) -> ExportResult:
    """Export raw HTML as a downloadable file."""
    _validate_html(html_content)
    content_bytes = html_content.encode("utf-8")
    return ExportResult(
        content=content_bytes,
        content_type="text/html",
        file_extension="html",
        filename=f"{_sanitize_title(options.document_title)}.html",
        metadata={
            "size_bytes": len(content_bytes),
            "encoding": "utf-8",
        },
    )


async def export_document(
    document_id: str,
    format_key: str,
    version: int | None = None,
    options: ExportOptions | None = None,
) -> ExportResult:
    """Export a document in the requested format."""
    try:
        # Get document HTML
        if version is not None:
            version_data = await session_service.get_version(document_id, version)
            if not version_data:
                raise ExportError(
                    f"Version {version} not found for document {document_id}"
                )
            html_content: str | None = version_data["html_content"]
        else:
            html_content = await session_service.get_latest_html(document_id)

        if not html_content:
            raise ExportError(
                f"Document {document_id} not found or has no content"
            )

        # Infographic detection: restrict to PNG only
        if is_infographic_html(html_content):
            if format_key.lower() != "png":
                raise ExportError(
                    "Infographic documents can only be exported as PNG"
                )
            if format_key.lower() == "png":
                from app.services.exporters.playwright_exporter import (
                    export_infographic_png,
                )

                if options is None:
                    options = ExportOptions(document_title=document_id[:50])
                return await export_infographic_png(html_content, options)

        # Look up exporter
        entry = _exporters.get(format_key.lower())
        if not entry:
            available = ", ".join(_exporters.keys())
            raise ExportError(
                f"Format '{format_key}' not supported. Available: {available}"
            )

        _format_name, exporter_fn = entry

        if options is None:
            options = ExportOptions(document_title=document_id[:50])

        logger.info(
            "Exporting document",
            document_id=document_id[:8],
            format=format_key,
            version=version,
        )

        result = await exporter_fn(html_content, options)

        logger.info(
            "Export successful",
            size_bytes=len(result.content),
            filename=result.filename,
        )
        return result

    except ExportError:
        raise
    except Exception as e:
        logger.error("Export failed", error=str(e), exc_info=True)
        raise ExportError(f"Export failed: {e}") from e


def list_available_formats() -> dict[str, str]:
    """Return a dict of format_key -> format_name."""
    return {k: name for k, (name, _fn) in _exporters.items()}
