"""
Image service for generating and embedding raster images in HTML documents.

Uses the Gemini API for image generation (base64 embedded).
Images are compressed with Pillow if > 5MB before embedding.
"""

import base64
from io import BytesIO

from PIL import Image
import structlog

from app.providers.base import ImageProvider, ImageResponse

logger = structlog.get_logger()

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


class ImageService:
    """Generate and embed images in HTML documents."""

    def __init__(
        self,
        image_provider: ImageProvider | None = None,
        fallback_provider: ImageProvider | None = None,
    ):
        self.image_provider = image_provider
        self.fallback_provider = fallback_provider

    async def generate_and_embed(
        self,
        current_html: str,
        prompt: str,
        resolution: str = "hd",
    ) -> tuple[str, ImageResponse]:
        """Generate raster image via API and embed as base64 in HTML."""
        if not self.image_provider:
            raise RuntimeError("No image provider configured")

        from app.config import settings
        from app.utils.image_retry import generate_image_with_retry

        img_response = await generate_image_with_retry(
            primary=self.image_provider,
            prompt=prompt,
            resolution=resolution,
            timeout=settings.image_timeout_seconds,
            fallback=self.fallback_provider,
            context="image",
        )

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


