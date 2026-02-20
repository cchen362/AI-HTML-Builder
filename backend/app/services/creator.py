"""
Document creation service using Gemini 2.5 Pro.

Creates new HTML documents from user prompts with optional template context.
Falls back to AnthropicProvider if Gemini is unavailable.
"""

from typing import AsyncIterator

import structlog

from app.providers.base import GenerationResult, LLMProvider

logger = structlog.get_logger()


CREATION_SYSTEM_PROMPT = """\
You are an expert HTML/CSS developer creating single-file HTML documents \
with modern design principles.

REQUIREMENTS:
1. Generate complete, valid HTML5 documents
2. All CSS must be inline in <style> tags
3. All JavaScript must be inline in <script> tags
4. No external dependencies or CDN links
5. Mobile-responsive with viewport meta tag
6. Use semantic HTML elements and ARIA attributes

DEFAULT STYLING (unless user specifies otherwise):
- Primary: Ink (#0F172A), Deep Teal (#0D7377), Teal (#14B8A6)
- Neutrals: Warm Slate (#334155), Stone (#78716C), Cream (#FAFAF9)
- Accent: Amber (#D97706), Mist (#CCFBF1), Emerald (#059669), Slate Blue (#475569)
- Background: Warm White (#F8FAFC)
- Typography: 'DM Sans', sans-serif — import from Google Fonts via \
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&display=swap" rel="stylesheet">
- Layout: CSS Grid/Flexbox with professional spacing
- Interactive: Smooth transitions (0.3s ease) and hover effects
- Accessibility: WCAG AA contrast, focus indicators, alt text

BEST PRACTICES:
- Semantic tags: <header>, <nav>, <main>, <section>, <article>, <footer>
- Mobile-first breakpoints: 768px (tablet), 1024px (desktop)
- Consistent spacing: 8px, 16px, 24px, 32px, 48px
- Shadows: box-shadow: 0 2px 4px rgba(0,0,0,0.1)
- Animations: transform, opacity (avoid layout shifts)

OUTPUT: Return ONLY complete HTML starting with <!DOCTYPE html>. \
No markdown fences, no explanation."""


class DocumentCreator:
    """Creates new HTML documents via LLM generation."""

    def __init__(
        self,
        provider: LLMProvider,
        fallback_provider: LLMProvider | None = None,
    ):
        self.provider = provider
        self.fallback = fallback_provider

    async def create(
        self,
        user_message: str,
        template_content: str | None = None,
        brand_spec: str | None = None,
    ) -> tuple[str, GenerationResult]:
        """Create a new document (non-streaming).

        Returns:
            (html_content, generation_result) for the caller to save.
        """
        system = CREATION_SYSTEM_PROMPT
        if brand_spec:
            system += f"\n\nBRAND GUIDELINES (override the default styling above with these):\n{brand_spec}"

        messages = self._build_messages(user_message, template_content)

        try:
            result = await self.provider.generate(
                system=system,
                messages=messages,
                max_tokens=24000,
                temperature=0.7,
            )
        except Exception as exc:
            if self.fallback:
                logger.warning(
                    "Primary creation provider failed, using fallback",
                    error=str(exc),
                )
                result = await self.fallback.generate(
                    system=system,
                    messages=messages,
                    max_tokens=24000,
                    temperature=0.7,
                )
            else:
                raise

        html = extract_html(result.text)
        return html, result

    async def stream_create(
        self,
        user_message: str,
        template_content: str | None = None,
        brand_spec: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream document creation. Yields text chunks.

        The caller is responsible for accumulating chunks, extracting HTML,
        and saving to the database.
        """
        system = CREATION_SYSTEM_PROMPT
        if brand_spec:
            system += f"\n\nBRAND GUIDELINES (override the default styling above with these):\n{brand_spec}"

        messages = self._build_messages(user_message, template_content)

        try:
            async for chunk in self.provider.stream(
                system=system,
                messages=messages,
                max_tokens=24000,
                temperature=0.7,
            ):
                yield chunk
        except Exception as exc:
            if self.fallback:
                logger.warning(
                    "Primary streaming failed, using fallback",
                    error=str(exc),
                )
                async for chunk in self.fallback.stream(
                    system=system,
                    messages=messages,
                    max_tokens=24000,
                    temperature=0.7,
                ):
                    yield chunk
            else:
                raise

    def _build_messages(
        self, user_message: str, template: str | None
    ) -> list[dict]:
        messages: list[dict] = []
        if template:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Here is the existing document to use as context "
                        "and source material:\n\n"
                        + template
                    ),
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I have the existing document. I'll use its content "
                        "as source material for the new document."
                    ),
                }
            )
        messages.append({"role": "user", "content": user_message})
        return messages


def extract_html(text: str) -> str:
    """Extract HTML document from LLM response text.

    Handles responses wrapped in markdown code fences or with preamble text.
    """
    # Strip markdown code fences
    cleaned = text
    if "```html" in cleaned:
        start = cleaned.index("```html") + len("```html")
        end = cleaned.rfind("```")
        if end > start:
            cleaned = cleaned[start:end].strip()

    # Find the actual HTML document
    if "<!DOCTYPE" in cleaned:
        start = cleaned.index("<!DOCTYPE")
        end = cleaned.rfind("</html>")
        if end > start:
            return cleaned[start : end + len("</html>")]

    return cleaned
