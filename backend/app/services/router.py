"""
LLM-based intent routing using Haiku 4.5.

Two rules:
1. No existing HTML → CREATE immediately (no LLM call)
2. HTML exists → Haiku 4.5 classifies into create / edit / image

Fallback on ANY error → edit (safest default: doesn't create docs or call image API).
"""

from __future__ import annotations

import re

import anthropic
import structlog

from app.config import settings

logger = structlog.get_logger()

# Pre-routing patterns (run BEFORE LLM, zero cost, zero latency)
_REMOVAL_RE = re.compile(
    r"\b(remove|delete|get rid of|take out|strip|eliminate)\b",
    re.IGNORECASE,
)

_TRANSFORM_RE = re.compile(
    r"("
    r"\bturn\s+(?:it\s+|this\s+|the\s+\S+\s+)?(?:into|to)\b"
    r"|\bconvert\s+(?:it\s+|this\s+|the\s+\S+\s+)?(?:into|to)\b"
    r"|\brewrite\s+(?:it\s+|this\s+)?(?:as|into)\b"
    r"|\bredo\s+(?:it\s+|this\s+)?(?:as|into)\b"
    r"|\bstart\s+(?:over|fresh|from\s+scratch)\b"
    r"|\binstead\s*$"
    r")",
    re.IGNORECASE,
)

_INFOGRAPHIC_RE = re.compile(
    r"\binfographics?\b",
    re.IGNORECASE,
)

_CLASSIFICATION_PROMPT = """Classify the user's intent into exactly one category.

CATEGORIES:
- create: User wants a NEW document, a completely different type of document, or to start over. Includes: "start fresh", standalone formats (infographic, mindmap, presentation, dashboard), or explicit new document requests.
- image: User wants to ADD a raster photo/picture/illustration INTO the existing document. The user is asking for a NEW visual to be ADDED.
- edit: User wants to MODIFY the existing document. Includes: text changes, styling, adding/removing sections, adding diagrams/charts/SVGs, removing images, or any change to the current document. This is the DEFAULT.

RULES:
- Removing/deleting/fixing anything → edit (NEVER image)
- "Turn into X" / "convert to Y" / "make it a Z" → create (complete document type change)
- Diagrams, charts, flowcharts, SVGs → edit (Claude generates these)
- If ambiguous → edit

Respond with ONLY one word: create, edit, or image"""

_VALID_ROUTES = frozenset({"create", "edit", "image", "infographic"})

# Lazy singleton — created on first LLM call, reused thereafter.
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


async def classify_request(user_input: str, has_existing_html: bool) -> str:
    """
    Classify the user's request into a routing category.

    Returns:
        'create'      - Route to Gemini 2.5 Pro for new document creation
        'infographic' - Route to InfographicService (2-LLM pipeline)
        'image'       - Route to Nano Banana Pro for raster image generation
        'edit'        - Route to Claude Sonnet 4.5 for surgical editing (DEFAULT)
    """
    # Rule 1: Removal/deletion intent → always EDIT (only with existing HTML)
    if has_existing_html and _REMOVAL_RE.search(user_input):
        logger.info("[ROUTER] Removal intent -> EDIT", request=user_input[:80])
        return "edit"

    # Rule 2: Infographic keyword → always INFOGRAPHIC (with or without HTML)
    if _INFOGRAPHIC_RE.search(user_input):
        logger.info("[ROUTER] Infographic intent -> INFOGRAPHIC", request=user_input[:80])
        return "infographic"

    # Rule 3: No existing HTML → always CREATE (no LLM call needed)
    if not has_existing_html:
        logger.info("[ROUTER] No existing HTML -> CREATE", request=user_input[:80])
        return "create"

    # Rule 4: Transform intent → CREATE (full document reconceptualization)
    if _TRANSFORM_RE.search(user_input):
        logger.info("[ROUTER] Transform intent -> CREATE", request=user_input[:80])
        return "create"

    # Rule 5: LLM classification via Haiku 4.5
    try:
        client = _get_client()
        response = await client.messages.create(
            model=settings.router_model,
            max_tokens=1,
            temperature=0,
            system=_CLASSIFICATION_PROMPT,
            messages=[{"role": "user", "content": user_input}],
        )

        route = response.content[0].text.strip().lower()  # type: ignore[union-attr]

        # Track cost
        usage = response.usage
        from app.services.cost_tracker import cost_tracker
        await cost_tracker.record_usage(
            settings.router_model,
            usage.input_tokens,
            usage.output_tokens,
        )

        if route in _VALID_ROUTES:
            logger.info(
                "[ROUTER] LLM classified",
                route=route,
                request=user_input[:80],
                tokens=usage.input_tokens + usage.output_tokens,
            )
            return route

        # Invalid response from LLM → default to edit
        logger.warning(
            "[ROUTER] Invalid LLM response, defaulting to EDIT",
            response=route,
            request=user_input[:80],
        )
        return "edit"

    except Exception as e:
        logger.error(
            "[ROUTER] LLM classification failed, defaulting to EDIT",
            error=str(e),
            request=user_input[:80],
        )
        return "edit"
