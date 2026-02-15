"""
Gemini 2.5 Pro provider for document creation.

Uses the google-genai SDK async API for text generation and streaming.
1M token context window, temperature 0.7 for creative generation.
NOT used for tool-based editing (that's AnthropicProvider's job).
"""

from typing import AsyncIterator

from google import genai
from google.genai import types

import structlog

from app.providers.base import (
    GenerationResult,
    LLMProvider,
)
from app.config import settings

logger = structlog.get_logger()


class GeminiProvider(LLMProvider):
    """Gemini provider for document creation and large-context tasks."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.google_api_key
        if not key:
            raise ValueError(
                "Google API key required (set GOOGLE_API_KEY env var)"
            )
        self.client = genai.Client(api_key=key)
        self.model = model or settings.creation_model

    async def generate(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> GenerationResult:
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,  # type: ignore[arg-type]
            config=config,
        )

        usage = response.usage_metadata
        input_toks: int = usage.prompt_token_count if usage else 0  # type: ignore[assignment]
        output_toks: int = usage.candidates_token_count if usage else 0  # type: ignore[assignment]
        text = response.text or ""

        if not text and response.candidates:
            candidate = response.candidates[0]
            logger.warning(
                "Gemini returned empty text",
                finish_reason=getattr(candidate, "finish_reason", None),
                safety_ratings=str(getattr(candidate, "safety_ratings", None)),
            )

        return GenerationResult(
            text=text,
            input_tokens=input_toks or 0,
            output_tokens=output_toks or 0,
            model=self.model,
        )

    async def stream(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        async for chunk in await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,  # type: ignore[arg-type]
            config=config,
        ):
            if chunk.text:
                yield chunk.text

    def _convert_messages(
        self, messages: list[dict]
    ) -> list[types.Content]:
        """Convert Anthropic-style messages to Gemini Content objects."""
        contents: list[types.Content] = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.get("content", ""))],
                )
            )
        return contents
