"""PDF and PNG exporters using Playwright headless Chromium."""

from __future__ import annotations

import structlog

from app.services.playwright_manager import playwright_manager
from .base import ExportError, ExportGenerationError, ExportOptions, ExportResult

logger = structlog.get_logger()


def _validate_html(html_content: str) -> None:
    """Validate HTML content before export."""
    if not html_content or not html_content.strip():
        raise ExportError("HTML content is empty")
    stripped = html_content.strip()
    if not stripped.startswith("<!DOCTYPE") and not stripped.startswith("<html"):
        raise ExportError("Invalid HTML: must start with <!DOCTYPE or <html>")


def _generate_filename(title: str, extension: str) -> str:
    """Generate sanitised filename for exported document."""
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in title
    ).strip()
    if not safe_title:
        safe_title = "document"
    return f"{safe_title}.{extension}"


async def _render_page(
    html_content: str,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
):
    """Create a Playwright page with content loaded. Caller must close the page."""
    page = await playwright_manager.create_page()
    await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
    await page.set_content(html_content, wait_until="networkidle")
    await page.wait_for_timeout(1000)
    return page


async def export_pdf(html_content: str, options: ExportOptions) -> ExportResult:
    """Export HTML as PDF via Playwright."""
    _validate_html(html_content)
    page = None
    try:
        page = await _render_page(html_content, 1920, 1080)

        pdf_bytes = await page.pdf(
            format=options.page_format,
            landscape=options.landscape,
            print_background=True,
            scale=options.scale,
            margin={
                "top": "0.5in",
                "right": "0.5in",
                "bottom": "0.5in",
                "left": "0.5in",
            },
        )

        return ExportResult(
            content=pdf_bytes,
            content_type="application/pdf",
            file_extension="pdf",
            filename=_generate_filename(options.document_title, "pdf"),
            metadata={
                "size_bytes": len(pdf_bytes),
                "page_format": options.page_format,
                "landscape": options.landscape,
                "rendered_with": "playwright-chromium",
            },
        )
    except ExportError:
        raise
    except Exception as e:
        logger.error("PDF export failed", error=str(e), exc_info=True)
        raise ExportGenerationError(f"PDF generation failed: {e}") from e
    finally:
        if page:
            await page.close()


async def export_png(html_content: str, options: ExportOptions) -> ExportResult:
    """Export HTML as PNG screenshot via Playwright."""
    _validate_html(html_content)
    page = None
    try:
        viewport_width = options.width or 1920
        viewport_height = options.height or 1080
        page = await _render_page(html_content, viewport_width, viewport_height)

        screenshot_kwargs: dict = {
            "full_page": options.full_page,
            "type": "png",
        }

        if options.width and options.height and not options.full_page:
            screenshot_kwargs["clip"] = {
                "x": 0,
                "y": 0,
                "width": options.width,
                "height": options.height,
            }

        png_bytes: bytes = await page.screenshot(**screenshot_kwargs)

        metadata: dict = {
            "size_bytes": len(png_bytes),
            "full_page": options.full_page,
            "rendered_with": "playwright-chromium",
        }
        if options.width and options.height:
            metadata["width"] = options.width
            metadata["height"] = options.height

        return ExportResult(
            content=png_bytes,
            content_type="image/png",
            file_extension="png",
            filename=_generate_filename(options.document_title, "png"),
            metadata=metadata,
        )
    except ExportError:
        raise
    except Exception as e:
        logger.error("PNG export failed", error=str(e), exc_info=True)
        raise ExportGenerationError(f"PNG generation failed: {e}") from e
    finally:
        if page:
            await page.close()
