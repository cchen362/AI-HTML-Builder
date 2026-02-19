"""AI-powered session title generation using Haiku 4.5."""

from __future__ import annotations

import re

import anthropic
import structlog

from app.config import settings

logger = structlog.get_logger()

# Same regex patterns used in chat.py — kept in sync
_BASE64_RE = re.compile(
    r"(data:image/[^;]+;base64,)[A-Za-z0-9+/=]{100,}",
)
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")

# Lazy singleton — created on first call, reused thereafter.
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _reset_client() -> None:
    """Clear the cached client singleton. Used by tests."""
    global _client
    _client = None


_TITLE_SYSTEM_PROMPT = """\
Generate a short, descriptive title for a chat session based on the user's message.

RULES:
- 3-5 words only
- Title Case
- No quotes, no punctuation, no trailing period
- Focus on WHAT the user is creating, not HOW
- Be specific and descriptive

EXAMPLES:
- Q3 Metrics Dashboard
- Sales Pitch Deck
- Team Onboarding Guide
- Product Launch Timeline
- Budget Impact Assessment

Respond with ONLY the title, nothing else."""


async def generate_session_title(
    user_message: str,
    template_name: str | None = None,
    user_content: str | None = None,
) -> str | None:
    """Generate a 3-5 word session title from the user's message.

    When a template is used, titles are based on user content (not the
    template prompt blob).  If the user sent a template with no custom
    content, returns None so the caller keeps the template-name title.

    Returns the title string on success, None on any failure.
    Never raises exceptions — safe for fire-and-forget usage.
    """
    try:
        # Template with no real user content — nothing to improve on
        if template_name and (not user_content or user_content == "(template only)"):
            return None

        # Pick the best input for title generation:
        # - With template + user content: use the user content (the actual topic)
        # - Without template: use the raw message
        raw = user_content if (template_name and user_content) else user_message

        # Clean input: strip base64 images and template placeholders
        cleaned = _BASE64_RE.sub("[image]", raw)
        cleaned = _PLACEHOLDER_RE.sub("", cleaned).strip()

        if not cleaned:
            return None

        # Truncate to first 500 chars (Haiku doesn't need more)
        cleaned = cleaned[:500]

        client = _get_client()
        response = await client.messages.create(
            model=settings.router_model,
            max_tokens=20,
            temperature=0,
            system=_TITLE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": cleaned}],  # type: ignore[arg-type]
        )

        title = response.content[0].text.strip()  # type: ignore[union-attr]

        # Track cost
        usage = response.usage
        from app.services.cost_tracker import cost_tracker

        await cost_tracker.record_usage(
            settings.router_model,
            usage.input_tokens,
            usage.output_tokens,
        )

        # Strip quotes that Haiku may wrap around the title
        title = title.strip("\"'")
        if not title:
            return None

        logger.info(
            "[TITLE] Generated session title",
            title=title,
            input_len=len(cleaned),
            tokens=usage.input_tokens + usage.output_tokens,
        )
        return title

    except Exception as e:
        logger.warning(
            "[TITLE] Title generation failed (non-critical)",
            error=str(e),
        )
        return None
