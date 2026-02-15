"""Shared image generation retry logic with fallback."""

from __future__ import annotations

import asyncio

import structlog

from app.providers.base import ImageProvider, ImageResponse

logger = structlog.get_logger()


async def generate_image_with_retry(
    primary: ImageProvider,
    prompt: str,
    resolution: str,
    timeout: float,
    fallback: ImageProvider | None = None,
    context: str = "image",
) -> ImageResponse:
    """Generate image with retry on primary, then fallback to secondary model.

    Strategy:
        1. Primary model, attempt 1 (timeout seconds)
        2. Primary model, attempt 2 — most 503s resolve on retry
        3. Fallback model (30s timeout) — different capacity pool
        4. Raise if all fail
    """
    # Attempt 1: Primary
    try:
        return await asyncio.wait_for(
            primary.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            f"{context.capitalize()} generation attempt 1 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 2: Primary retry
    try:
        return await asyncio.wait_for(
            primary.generate_image(prompt, resolution),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, RuntimeError, Exception) as e:
        logger.warning(
            f"{context.capitalize()} generation attempt 2 failed",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Attempt 3: Fallback model
    if fallback:
        logger.info(f"Falling back to secondary {context} model")
        try:
            return await asyncio.wait_for(
                fallback.generate_image(prompt, resolution),
                timeout=30,
            )
        except (asyncio.TimeoutError, RuntimeError, Exception) as e:
            logger.error(
                f"Fallback {context} generation failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(
                f"{context.capitalize()} generation failed after all attempts"
            ) from e

    raise RuntimeError(
        f"{context.capitalize()} generation failed and no fallback configured"
    )
