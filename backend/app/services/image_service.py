"""
Image service for generating and embedding images in HTML documents.

Supports two modes:
1. SVG templates for diagrams/charts (zero API cost)
2. Gemini API for raster images (base64 embedded)

Images are compressed with Pillow if > 5MB before embedding.
"""

import asyncio
import base64
import re
from io import BytesIO

from PIL import Image
import structlog

from app.providers.base import ImageProvider, ImageResponse

logger = structlog.get_logger()

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

SVG_KEYWORDS: dict[str, str] = {
    "flowchart": "flowchart",
    "flow chart": "flowchart",
    "process flow": "flowchart",
    "diagram": "flowchart",
    "chart": "chart",
    "bar chart": "chart",
    "pie chart": "chart",
    "graph": "chart",
    "timeline": "timeline",
    "hierarchy": "flowchart",
    "org chart": "flowchart",
    "mind map": "flowchart",
}


class ImageService:
    """Generate and embed images in HTML documents."""

    def __init__(
        self,
        image_provider: ImageProvider | None = None,
        fallback_provider: ImageProvider | None = None,
    ):
        self.image_provider = image_provider
        self.fallback_provider = fallback_provider

    async def _generate_with_retry(
        self,
        prompt: str,
        resolution: str,
    ) -> ImageResponse:
        """Generate image with retry on primary, then fallback to secondary model.

        Strategy:
            1. Primary model, attempt 1 (90s timeout)
            2. Primary model, attempt 2 (90s timeout) — most 503s resolve on retry
            3. Fallback model (30s timeout) — different capacity pool
            4. Raise if all fail
        """
        from app.config import settings

        timeout = settings.image_timeout_seconds

        if not self.image_provider:
            raise RuntimeError("No image provider configured")

        # Attempt 1: Primary
        try:
            return await asyncio.wait_for(
                self.image_provider.generate_image(prompt, resolution),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.warning(
                "Image generation attempt 1 failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Attempt 2: Primary retry
        try:
            return await asyncio.wait_for(
                self.image_provider.generate_image(prompt, resolution),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.warning(
                "Image generation attempt 2 failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Attempt 3: Fallback model
        if self.fallback_provider:
            logger.info("Falling back to secondary image model")
            try:
                return await asyncio.wait_for(
                    self.fallback_provider.generate_image(prompt, resolution),
                    timeout=30,
                )
            except (asyncio.TimeoutError, RuntimeError, Exception) as e:
                logger.error(
                    "Fallback image generation failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise RuntimeError(
                    "Image generation failed after all attempts"
                ) from e
        else:
            raise RuntimeError(
                "Image generation failed and no fallback model configured"
            )

    def should_use_svg(self, message: str) -> tuple[bool, str]:
        """Check if SVG template is appropriate for this request.

        Uses word-boundary matching to avoid false positives
        (e.g. "infographic" should NOT match "graph").

        Returns:
            (use_svg, svg_type) - e.g. (True, "flowchart")
        """
        msg_lower = message.lower()
        for keyword, svg_type in SVG_KEYWORDS.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', msg_lower):
                return True, svg_type
        return False, ""

    async def generate_and_embed(
        self,
        current_html: str,
        prompt: str,
        resolution: str = "hd",
    ) -> tuple[str, ImageResponse]:
        """Generate raster image via API and embed as base64 in HTML."""
        if not self.image_provider:
            raise RuntimeError("No image provider configured")

        img_response = await self._generate_with_retry(prompt, resolution)

        image_bytes = img_response.image_bytes
        if len(image_bytes) > MAX_IMAGE_SIZE:
            logger.info(
                "Compressing image",
                original_size=len(image_bytes),
            )
            image_bytes = _compress_image(image_bytes, img_response.format)

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime = f"image/{img_response.format.lower()}"

        img_html = (
            '<div class="generated-image" '
            'style="margin:20px 0;text-align:center;">'
            f'<img src="data:{mime};base64,{b64}" '
            f'alt="{_escape_attr(prompt[:100])}" '
            'style="max-width:100%;height:auto;border-radius:8px;'
            'box-shadow:0 4px 6px rgba(0,0,0,0.1);"/>'
            "</div>"
        )

        updated_html = _insert_into_html(current_html, img_html)
        return updated_html, img_response

    def generate_svg_and_embed(
        self, current_html: str, svg_type: str, description: str
    ) -> str:
        """Generate SVG from template and embed in HTML (zero cost)."""
        svg = _get_svg_template(svg_type, description)
        svg_html = (
            '<div class="generated-svg" '
            f'style="margin:20px 0;text-align:center;">{svg}</div>'
        )
        return _insert_into_html(current_html, svg_html)


def _escape_attr(text: str) -> str:
    """Escape text for use in HTML attributes."""
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _insert_into_html(html: str, content: str) -> str:
    """Insert content before </main> or </body>."""
    if "</main>" in html:
        return html.replace("</main>", f"{content}\n</main>", 1)
    if "</body>" in html:
        return html.replace("</body>", f"{content}\n</body>", 1)
    return html + content


def _compress_image(image_bytes: bytes, fmt: str) -> bytes:
    """Compress image to stay under MAX_IMAGE_SIZE."""
    img = Image.open(BytesIO(image_bytes))

    # Try reducing quality first (JPEG only)
    if fmt.upper() != "PNG":
        quality = 85
        while quality >= 50:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if len(buf.getvalue()) <= MAX_IMAGE_SIZE:
                return buf.getvalue()
            quality -= 10

    # Resize as last resort
    img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
    buf = BytesIO()
    save_fmt = "JPEG" if fmt.upper() != "PNG" else "PNG"
    if save_fmt == "JPEG":
        img.save(buf, format=save_fmt, quality=75, optimize=True)
    else:
        img.save(buf, format=save_fmt, optimize=True)

    logger.info("Image compressed", final_size=len(buf.getvalue()))
    return buf.getvalue()


def _get_svg_template(svg_type: str, description: str) -> str:
    """Return SVG markup for the given diagram type."""
    if svg_type == "flowchart":
        return _flowchart_svg()
    if svg_type == "chart":
        return _chart_svg()
    if svg_type == "timeline":
        return _timeline_svg()
    return _placeholder_svg(description)


def _flowchart_svg() -> str:
    return (
        '<svg width="600" height="320" xmlns="http://www.w3.org/2000/svg">'
        "<defs>"
        '<marker id="ah" markerWidth="10" markerHeight="7" '
        'refX="9" refY="3.5" orient="auto">'
        '<polygon points="0 0,10 3.5,0 7" fill="#0D7377"/>'
        "</marker>"
        "</defs>"
        '<rect x="225" y="20" width="150" height="50" rx="25" fill="#0D7377"/>'
        '<text x="300" y="50" text-anchor="middle" fill="#fff" '
        'font-family="DM Sans,sans-serif" font-size="14">Start</text>'
        '<line x1="300" y1="70" x2="300" y2="110" stroke="#0D7377" '
        'stroke-width="2" marker-end="url(#ah)"/>'
        '<rect x="225" y="120" width="150" height="50" fill="#14B8A6"/>'
        '<text x="300" y="150" text-anchor="middle" fill="#fff" '
        'font-family="DM Sans,sans-serif" font-size="14">Process</text>'
        '<line x1="300" y1="170" x2="300" y2="210" stroke="#0D7377" '
        'stroke-width="2" marker-end="url(#ah)"/>'
        '<rect x="225" y="220" width="150" height="50" rx="25" fill="#059669"/>'
        '<text x="300" y="250" text-anchor="middle" fill="#fff" '
        'font-family="DM Sans,sans-serif" font-size="14">End</text>'
        "</svg>"
    )


def _chart_svg() -> str:
    return (
        '<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">'
        '<line x1="50" y1="350" x2="550" y2="350" stroke="#334155" stroke-width="2"/>'
        '<line x1="50" y1="50" x2="50" y2="350" stroke="#334155" stroke-width="2"/>'
        '<rect x="100" y="200" width="60" height="150" fill="#0D7377"/>'
        '<rect x="200" y="150" width="60" height="200" fill="#14B8A6"/>'
        '<rect x="300" y="100" width="60" height="250" fill="#0D7377"/>'
        '<rect x="400" y="180" width="60" height="170" fill="#14B8A6"/>'
        '<text x="130" y="370" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="12">Q1</text>'
        '<text x="230" y="370" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="12">Q2</text>'
        '<text x="330" y="370" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="12">Q3</text>'
        '<text x="430" y="370" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="12">Q4</text>'
        "</svg>"
    )


def _timeline_svg() -> str:
    return (
        '<svg width="800" height="200" xmlns="http://www.w3.org/2000/svg">'
        '<line x1="50" y1="100" x2="750" y2="100" stroke="#0D7377" stroke-width="3"/>'
        '<circle cx="150" cy="100" r="8" fill="#0D7377"/>'
        '<circle cx="350" cy="100" r="8" fill="#0D7377"/>'
        '<circle cx="550" cy="100" r="8" fill="#0D7377"/>'
        '<circle cx="750" cy="100" r="8" fill="#059669"/>'
        '<text x="150" y="140" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="14">Phase 1</text>'
        '<text x="350" y="140" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="14">Phase 2</text>'
        '<text x="550" y="140" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="14">Phase 3</text>'
        '<text x="750" y="140" text-anchor="middle" '
        'font-family="DM Sans,sans-serif" font-size="14">Complete</text>'
        "</svg>"
    )


def _placeholder_svg(description: str) -> str:
    safe_desc = _escape_attr(description[:50])
    return (
        '<svg width="600" height="300" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="600" height="300" fill="#F8FAFC"/>'
        f'<text x="300" y="150" text-anchor="middle" '
        f'font-family="DM Sans,sans-serif" font-size="18" '
        f'fill="#334155">{safe_desc}</text>'
        "</svg>"
    )
