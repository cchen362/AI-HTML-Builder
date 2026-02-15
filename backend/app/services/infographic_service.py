"""
Two-LLM infographic pipeline: Gemini 2.5 Pro (art director) → Nano Banana Pro (renderer).

The art director reads user content and style direction, then writes a detailed visual
prompt describing layout, text, colors, and imagery. Nano Banana Pro renders that prompt
into a 2K raster infographic. Each iteration is a full regeneration — the art director
modifies its previous visual prompt based on user feedback.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass

import structlog

from app.providers.base import ImageProvider, ImageResponse, LLMProvider

logger = structlog.get_logger()


@dataclass
class InfographicResult:
    """Result from the infographic generation pipeline."""

    image_bytes: bytes
    image_format: str  # "PNG" or "JPEG"
    visual_prompt: str  # The prompt sent to Nano Banana Pro
    model_prompt: str  # Art director model (e.g., "gemini-2.5-pro")
    model_image: str  # Renderer model (e.g., "gemini-3-pro-image-preview")
    prompt_input_tokens: int
    prompt_output_tokens: int


ART_DIRECTOR_SYSTEM_PROMPT = """\
You are an expert infographic art director. Your job is to write a detailed \
visual prompt that an AI image generation model will use to create a stunning, \
professional infographic.

YOUR OUTPUT is a text prompt — NOT an image, NOT code, NOT HTML.

RULES:
1. Describe a COMPLETE infographic layout in vivid, precise detail
2. Specify exact text, numbers, and labels — the image model renders text literally, \
so every word must be exactly as it should appear
3. Describe visual hierarchy: what is large/prominent, what is secondary
4. Specify a color palette (hex codes or descriptive names)
5. Describe the typography style (bold headlines, clean body text, etc.)
6. Describe data visualizations concretely (bar chart with specific values, etc.)
7. Include decorative elements: icons, illustrations, divider lines, backgrounds
8. Canvas: 2560x1440 pixels, landscape orientation
9. Style: magazine-quality, modern, professional infographic
10. Keep ALL text in the infographic SHORT — titles 3-6 words, bullets 5-10 words max
11. Maximum 5-7 sections/blocks — do not cram too much information

AVOID:
- Generic descriptions ("nice colors", "clean layout")
- Vague text placeholders ("add a title here")
- More than 200 words of body text total in the infographic — it must be VISUAL
- Tiny text that would be illegible at 2560x1440

OUTPUT: Return ONLY the visual prompt. No markdown, no code fences, no explanation.\
"""


class InfographicService:
    """Two-LLM pipeline: Gemini 2.5 Pro (art director) → Nano Banana Pro (renderer)."""

    def __init__(
        self,
        prompt_provider: LLMProvider,
        image_provider: ImageProvider,
        fallback_image_provider: ImageProvider | None = None,
    ):
        self.prompt_provider = prompt_provider
        self.image_provider = image_provider
        self.fallback_image_provider = fallback_image_provider

    async def generate(
        self,
        user_message: str,
        content_context: str | None = None,
        previous_visual_prompt: str | None = None,
    ) -> InfographicResult:
        """Generate an infographic via the two-LLM pipeline.

        Args:
            user_message: The user's request (e.g., "make an infographic about Q4 revenue")
            content_context: Existing HTML doc content (base64-stripped) for first-time creation.
                            Passed when transforming an existing document into an infographic.
            previous_visual_prompt: The art director's previous visual prompt, for iteration.
                                  Passed when user is refining an existing infographic.
        """
        # Step 1: Art Director — generate visual prompt
        messages = self._build_messages(user_message, content_context, previous_visual_prompt)

        logger.info(
            "Infographic art director generating visual prompt",
            user_message=user_message[:80],
            has_context=content_context is not None,
            is_iteration=previous_visual_prompt is not None,
        )

        # Retry once on empty — Gemini 2.5 Pro sporadically returns
        # finish_reason=MAX_TOKENS with 0 output tokens on first attempt.
        visual_prompt = ""
        for art_attempt in range(2):
            result = await self.prompt_provider.generate(
                system=ART_DIRECTOR_SYSTEM_PROMPT,
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
            )
            visual_prompt = result.text.strip()

            logger.info(
                "Visual prompt generated",
                prompt_length=len(visual_prompt),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                attempt=art_attempt + 1,
            )

            if visual_prompt:
                break

            logger.warning(
                "Art director returned empty prompt, retrying",
                attempt=art_attempt + 1,
                input_tokens=result.input_tokens,
            )

        if not visual_prompt:
            logger.error(
                "Art director returned empty visual prompt after retries",
                input_tokens=result.input_tokens,
                user_message=user_message[:80],
            )
            raise RuntimeError(
                "The art director couldn't generate a design prompt for this request. "
                "Try rephrasing or simplifying your instructions."
            )

        # Step 2: Renderer — generate image from visual prompt
        img_response = await self._generate_image_with_retry(visual_prompt, "2k")

        # Compress if needed
        image_bytes = img_response.image_bytes
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
            from app.services.image_service import _compress_image

            image_bytes = _compress_image(image_bytes, img_response.format)

        return InfographicResult(
            image_bytes=image_bytes,
            image_format=img_response.format,
            visual_prompt=visual_prompt,
            model_prompt=result.model,
            model_image=img_response.model,
            prompt_input_tokens=result.input_tokens,
            prompt_output_tokens=result.output_tokens,
        )

    def _build_messages(
        self,
        user_message: str,
        content_context: str | None,
        previous_visual_prompt: str | None,
    ) -> list[dict]:  # type: ignore[type-arg]
        """Build the message chain for the art director.

        Two modes:
        - First creation: content_context (existing doc HTML) as source material
        - Iteration: previous_visual_prompt (art director's last spec) for modification
        """
        messages: list[dict] = []  # type: ignore[type-arg]

        # Source material (existing doc content, for first-time creation)
        if content_context:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Here is the source content to create an infographic from:\n\n"
                        + content_context
                    ),
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I have the source content. I'll design a visual infographic "
                        "prompt based on this material."
                    ),
                }
            )

        # Previous visual prompt (for iteration — the art director's last spec)
        if previous_visual_prompt:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Here is the visual prompt you previously created for this "
                        "infographic:\n\n" + previous_visual_prompt
                    ),
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I have my previous visual prompt. I'll modify it based "
                        "on the new feedback."
                    ),
                }
            )

        # Current user request
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _generate_image_with_retry(
        self,
        prompt: str,
        resolution: str,
    ) -> ImageResponse:
        """Generate image with retry on primary, then fallback to secondary model.

        Strategy (identical to ImageService):
            1. Primary model, attempt 1 (timeout from settings)
            2. Primary model, attempt 2 — most 503s resolve on retry
            3. Fallback model (30s timeout) — different capacity pool
        """
        from app.config import settings

        timeout = settings.image_timeout_seconds

        # Attempt 1: Primary
        try:
            return await asyncio.wait_for(
                self.image_provider.generate_image(prompt, resolution),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.warning(
                "Infographic image attempt 1 failed",
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
                "Infographic image attempt 2 failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Attempt 3: Fallback model
        if self.fallback_image_provider:
            logger.info("Falling back to secondary image model for infographic")
            try:
                return await asyncio.wait_for(
                    self.fallback_image_provider.generate_image(prompt, resolution),
                    timeout=30,
                )
            except (asyncio.TimeoutError, RuntimeError, Exception) as e:
                logger.error(
                    "Fallback infographic image generation failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise RuntimeError(
                    "Infographic image generation failed after all attempts"
                ) from e
        else:
            raise RuntimeError(
                "Infographic image generation failed and no fallback configured"
            )


def wrap_infographic_html(
    image_bytes: bytes, image_format: str, alt_text: str
) -> str:
    """Wrap infographic image bytes in a minimal HTML document.

    The HTML structure is intentionally minimal — no <main>, <header>, <section>.
    This distinctness is used by _is_infographic_doc() in chat.py to detect
    infographic documents for iteration routing.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = f"image/{image_format.lower()}"
    safe_alt = alt_text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")[:200]

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1">'
        "<title>Infographic</title>\n"
        "<style>*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#0a0a0f;display:flex;justify-content:center;"
        "align-items:center;min-height:100vh}"
        "img{max-width:100%;height:auto;display:block}</style>\n"
        "</head>\n"
        f'<body><img src="data:{mime};base64,{b64}" '
        f'alt="{safe_alt}"/></body>\n'
        "</html>"
    )
