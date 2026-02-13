"""
Nano Banana Pro (Gemini 3 Pro Image) generation provider.

Uses the google-genai SDK to generate images from text prompts.
Returns PNG/JPEG bytes for base64 embedding in HTML documents.
Fallback to Nano Banana Flash (gemini-2.5-flash-image) handled by ImageService.
"""

from google import genai
from google.genai import types

import structlog

from app.providers.base import ImageProvider, ImageResponse
from app.config import settings

logger = structlog.get_logger()

# Approximate dimensions for each resolution tier
_RESOLUTION_DIMS: dict[str, tuple[int, int]] = {
    "4k": (3840, 2160),
    "2k": (2560, 1440),
    "hd": (1920, 1080),
    "sd": (1280, 720),
}


class GeminiImageProvider(ImageProvider):
    """Gemini image provider for raster image generation."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.google_api_key
        if not key:
            raise ValueError(
                "Google API key required (set GOOGLE_API_KEY env var)"
            )
        self.client = genai.Client(api_key=key)
        self.model = model or settings.image_model

    async def generate_image(
        self,
        prompt: str,
        resolution: str = "2k",
    ) -> ImageResponse:
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        )

        logger.info(
            "Generating image",
            prompt=prompt[:100],
            resolution=resolution,
            model=self.model,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        # Extract image from response parts
        if response.candidates:
            content = response.candidates[0].content
            if content and content.parts:
                for part in content.parts:
                    if part.inline_data is not None:
                        image_bytes: bytes = part.inline_data.data  # type: ignore[assignment]
                        mime_type = part.inline_data.mime_type or "image/png"
                        fmt = "PNG" if "png" in mime_type.lower() else "JPEG"
                        w, h = _RESOLUTION_DIMS.get(
                            resolution.lower(), (2560, 1440)
                        )

                        logger.info(
                            "Image generated",
                            size=len(image_bytes),
                            format=fmt,
                        )

                        return ImageResponse(
                            image_bytes=image_bytes,
                            format=fmt,
                            width=w,
                            height=h,
                            model=self.model,
                            prompt=prompt,
                        )

        raise RuntimeError("No image data in Gemini response")
