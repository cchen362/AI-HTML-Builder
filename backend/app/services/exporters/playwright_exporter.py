"""PDF and PNG exporters using Playwright headless Chromium."""

from __future__ import annotations

import base64
import re

import structlog

from app.services.playwright_manager import playwright_manager
from .base import ExportError, ExportGenerationError, ExportOptions, ExportResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Print CSS for better PDF page breaking
# ---------------------------------------------------------------------------

_PRINT_CSS = """\
@media print {
  section, article, blockquote, figure, table, ul, ol, dl,
  details, fieldset, pre {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  h1, h2, h3, h4, h5, h6 {
    break-after: avoid;
    page-break-after: avoid;
  }
  h1 + *, h2 + *, h3 + * {
    break-before: avoid;
  }
  div[style*="border-radius"], div[style*="box-shadow"] {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  p { orphans: 3; widows: 3; }
  img { max-height: 90vh; }
}"""


def _inject_print_css(html: str) -> str:
    """Inject print-friendly CSS before </head> for better page breaking.

    Only affects @media print — no visual change to screen rendering.
    Returns html unchanged if </head> is not found.
    """
    tag = "</head>"
    if tag not in html:
        return html
    return html.replace(tag, f"<style>{_PRINT_CSS}</style>\n{tag}", 1)


# ---------------------------------------------------------------------------
# Infographic direct image extraction
# ---------------------------------------------------------------------------

# Regex to extract image format and base64 payload from data URI
_DATA_URI_IMAGE_RE = re.compile(
    r'data:image/([a-zA-Z0-9+.-]+);base64,([A-Za-z0-9+/=]+)'
)


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
    html_content = _inject_print_css(html_content)
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


async def export_infographic_png(
    html_content: str, options: ExportOptions
) -> ExportResult:
    """Export infographic by extracting raw image bytes from base64 HTML.

    No Playwright rendering — direct base64 decode preserves full
    original resolution (typically 2560x1440).
    """
    match = _DATA_URI_IMAGE_RE.search(html_content)
    if not match:
        raise ExportError("No embedded image found in infographic HTML")

    image_format = match.group(1).lower()  # "png", "jpeg", etc.
    b64_data = match.group(2)

    try:
        image_bytes = base64.b64decode(b64_data)
    except Exception as e:
        raise ExportGenerationError(
            f"Failed to decode infographic image: {e}"
        ) from e

    # Normalize format for content type and extension
    ext = "jpg" if image_format == "jpeg" else image_format
    content_type = f"image/{image_format}"

    return ExportResult(
        content=image_bytes,
        content_type=content_type,
        file_extension=ext,
        filename=_generate_filename(options.document_title, ext),
        metadata={
            "size_bytes": len(image_bytes),
            "source": "direct-base64-extraction",
            "original_format": image_format,
        },
    )
