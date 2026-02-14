from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import re
import structlog

logger = structlog.get_logger()
router = APIRouter()

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


def _extract_title(message: str) -> str:
    """Extract a clean document title from the user message.

    Handles template messages like:
        'Create an engaging slide presentation about: {{TOPIC}}\\n\\nContent'
    by stripping the placeholder and trailing punctuation.
    """
    first_line = message.split("\n")[0]

    if _PLACEHOLDER_RE.search(first_line):
        clean = _PLACEHOLDER_RE.sub("", first_line).strip().rstrip(":").strip()
        if clean:
            return clean[:50]

    return first_line[:50]


_BASE64_RE = re.compile(
    r'(data:image/[^;]+;base64,)[A-Za-z0-9+/=]{100,}',
)


def _strip_base64_for_context(html: str) -> str:
    """Strip base64 image payloads from HTML for use as LLM context.

    Preserves <img> tags and alt text but replaces the base64 payload
    with a placeholder. Gemini can't interpret base64 in text form —
    it's pure noise that wastes tokens and cost.
    """
    return _BASE64_RE.sub(r'\1[image-removed]', html)


def _is_infographic_doc(html: str) -> bool:
    """Detect infographic wrapper docs (minimal HTML with single base64 <img>).

    Infographic documents have a distinctive structure: <500 chars of HTML
    after removing base64 payloads, with a single <img> tag. This is how
    wrap_infographic_html() creates them — no <main>, <header>, <section>.

    Regular docs with embedded images are excluded by checking for structural
    HTML tags that infographic wrappers never contain.
    """
    stripped = _BASE64_RE.sub("", html)
    if len(stripped) >= 600:
        return False
    if "<img" not in html or "data:image" not in html:
        return False
    # Infographic wrappers have no structural content tags
    lower = html.lower()
    if "<main" in lower or "<header" in lower or "<section" in lower:
        return False
    return True


async def _get_latest_version_prompt(
    session_service: Any, document_id: str
) -> str | None:
    """Get the art director's visual prompt from version history.

    Walks backwards through version history (DESC order) and returns the
    first non-empty visual_prompt. This provides resilience against versions
    that were saved without a visual prompt (e.g., failed edits before the
    route override fix).
    """
    history = await session_service.get_version_history(document_id)
    for version in history:
        prompt = version.get("visual_prompt")
        if prompt:
            return prompt
    return None


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


class ChatRequest(BaseModel):
    message: str
    document_id: str | None = None  # If None, uses active document


# ---------------------------------------------------------------------------
# Handler generators — each yields dicts, caller wraps with _sse()
# ---------------------------------------------------------------------------


async def _handle_edit(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    active_doc: dict,
    current_html: str,
) -> AsyncIterator[dict]:
    """Surgical edit via Claude tool_use."""
    from app.services.editor import SurgicalEditor
    from app.providers.anthropic_provider import AnthropicProvider
    from app.services.cost_tracker import cost_tracker

    yield {"type": "status", "content": "Editing..."}

    editor = SurgicalEditor(AnthropicProvider())
    chat_history = await session_service.get_chat_history(
        session_id, limit=8
    )

    result = await editor.edit(
        current_html, request.message, chat_history
    )

    # Save new version
    version = await session_service.save_version(
        active_doc["id"],
        result.html,
        user_prompt=request.message,
        edit_summary=result.edit_summary,
        model_used=result.model,
        tokens_used=result.input_tokens + result.output_tokens,
    )

    # Track cost
    await cost_tracker.record_usage(
        result.model,
        result.input_tokens,
        result.output_tokens,
    )

    # Save assistant message
    await session_service.add_chat_message(
        session_id,
        "assistant",
        result.edit_summary,
        active_doc["id"],
        "edit_confirmation",
    )

    yield {"type": "html", "content": result.html, "version": version}
    yield {"type": "summary", "content": result.edit_summary}


async def _handle_create(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    current_html: str | None = None,
) -> AsyncIterator[dict]:
    """New document via Gemini (Claude fallback)."""
    from app.services.creator import DocumentCreator, extract_html
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.anthropic_provider import AnthropicProvider
    from app.services.cost_tracker import cost_tracker

    yield {"type": "status", "content": "Creating document..."}

    try:
        primary = GeminiProvider()
        fallback = AnthropicProvider()
    except ValueError:
        # No Google API key — use Claude only
        primary = AnthropicProvider()  # type: ignore[assignment]
        fallback = None  # type: ignore[assignment]

    creator = DocumentCreator(primary, fallback)

    # Strip base64 from context (noise for Gemini, wastes tokens)
    context_html = None
    if current_html:
        context_html = _strip_base64_for_context(current_html)

    # Stream creation
    chunks: list[str] = []
    async for chunk in creator.stream_create(
        request.message, template_content=context_html
    ):
        chunks.append(chunk)
        yield {"type": "chunk", "content": chunk}

    full_html = extract_html("".join(chunks))
    title = _extract_title(request.message)

    new_doc_id = await session_service.create_document(
        session_id, title
    )

    # Estimate tokens (streaming doesn't return usage metadata)
    context_len = len(context_html) if context_html else 0
    est_input = (len(request.message) + context_len) // 4
    est_output = len(full_html) // 4
    model_used = getattr(primary, "model", "unknown")

    version = await session_service.save_version(
        new_doc_id,
        full_html,
        user_prompt=request.message,
        edit_summary=f"Created: {title}",
        model_used=model_used,
        tokens_used=est_input + est_output,
    )

    await cost_tracker.record_usage(
        model_used, est_input, est_output
    )

    await session_service.add_chat_message(
        session_id,
        "assistant",
        f"Created: {title}",
        new_doc_id,
        "create_confirmation",
    )

    yield {"type": "html", "content": full_html, "version": version}
    yield {"type": "summary", "content": f"Created: {title}"}


async def _handle_image(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    active_doc: dict | None,
    current_html: str | None,
) -> AsyncIterator[dict]:
    """Raster image generation via Gemini."""
    from app.services.image_service import ImageService
    from app.services.cost_tracker import cost_tracker

    yield {"type": "status", "content": "Generating image..."}

    if not active_doc or not current_html:
        yield {
            "type": "error",
            "content": "No document to add image to. Create a document first.",
        }
        return

    # Initialise image provider
    try:
        from app.providers.gemini_image_provider import GeminiImageProvider
        img_provider = GeminiImageProvider()
    except (ValueError, Exception):
        img_provider = None  # type: ignore[assignment]

    if not img_provider:
        yield {
            "type": "error",
            "content": "Image generation unavailable (no GOOGLE_API_KEY).",
        }
        return

    img_fallback = None  # type: ignore[assignment]
    try:
        from app.config import settings as _settings
        img_fallback = GeminiImageProvider(
            model=_settings.image_fallback_model,
        )
    except (ValueError, Exception):
        pass  # No fallback available, primary only

    img_service = ImageService(
        img_provider,
        fallback_provider=img_fallback,
    )

    gen_task = asyncio.create_task(
        img_service.generate_and_embed(
            current_html,
            request.message,
            resolution="hd",
        )
    )
    timer_task = asyncio.create_task(asyncio.sleep(8))

    done, _pending = await asyncio.wait(
        {gen_task, timer_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if timer_task in done and gen_task not in done:
        yield {
            "type": "status",
            "content": "Still generating... high-quality images can take 15-30 seconds",
        }
        updated_html, img_resp = await gen_task
    else:
        timer_task.cancel()
        updated_html, img_resp = gen_task.result()

    model_used = img_resp.model

    version = await session_service.save_version(
        active_doc["id"],
        updated_html,
        user_prompt=request.message,
        edit_summary="Added image to document",
        model_used=model_used,
        tokens_used=0,
    )

    await cost_tracker.record_usage(
        model_used, 0, 0, 1
    )

    await session_service.add_chat_message(
        session_id,
        "assistant",
        "Added image to document",
        active_doc["id"],
        "image_confirmation",
    )

    yield {
        "type": "html",
        "content": updated_html,
        "version": version,
    }
    yield {
        "type": "summary",
        "content": "Added image to document",
    }


async def _handle_infographic(
    session_service: Any,
    request: ChatRequest,
    session_id: str,
    active_doc: dict | None,
    current_html: str | None,
) -> AsyncIterator[dict]:
    """Infographic generation via Gemini 2.5 Pro (art director) + Nano Banana Pro (renderer)."""
    from app.services.infographic_service import (
        InfographicService,
        wrap_infographic_html,
    )
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.gemini_image_provider import GeminiImageProvider
    from app.services.cost_tracker import cost_tracker

    yield {"type": "status", "content": "Designing infographic..."}

    # Initialize prompt provider (Gemini 2.5 Pro)
    try:
        prompt_provider = GeminiProvider()
    except ValueError:
        yield {
            "type": "error",
            "content": "Infographic generation unavailable (no GOOGLE_API_KEY).",
        }
        return

    # Initialize image provider (Nano Banana Pro)
    try:
        img_provider = GeminiImageProvider()
    except (ValueError, Exception):
        yield {
            "type": "error",
            "content": "Image generation unavailable (no GOOGLE_API_KEY).",
        }
        return

    # Initialize fallback image provider
    img_fallback = None
    try:
        from app.config import settings as _settings

        img_fallback = GeminiImageProvider(model=_settings.image_fallback_model)
    except (ValueError, Exception):
        pass  # No fallback available

    service = InfographicService(prompt_provider, img_provider, img_fallback)

    # Determine context mode: first creation vs. iteration
    content_context = None
    previous_visual_prompt = None
    is_iteration = False

    if active_doc and current_html and _is_infographic_doc(current_html):
        # Active doc IS an infographic → iteration mode
        is_iteration = True
        previous_visual_prompt = await _get_latest_version_prompt(
            session_service, active_doc["id"]
        )
    elif current_html:
        # Active doc is a regular HTML doc → use as source material
        content_context = _strip_base64_for_context(current_html)

    # Generate infographic with progress updates
    gen_task = asyncio.create_task(
        service.generate(
            request.message,
            content_context=content_context,
            previous_visual_prompt=previous_visual_prompt,
        )
    )
    timer_task = asyncio.create_task(asyncio.sleep(8))

    done, _pending = await asyncio.wait(
        {gen_task, timer_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if timer_task in done and gen_task not in done:
        yield {
            "type": "status",
            "content": "Rendering infographic... high-quality images can take 15-30 seconds",
        }
        result = await gen_task
    else:
        timer_task.cancel()
        result = gen_task.result()

    # Wrap image in HTML
    infographic_html = wrap_infographic_html(
        result.image_bytes,
        result.image_format,
        alt_text=f"Infographic: {request.message[:100]}",
    )

    title = f"Infographic: {_extract_title(request.message)}"
    model_used = f"{result.model_prompt}+{result.model_image}"

    if is_iteration and active_doc:
        # Iteration: new version of existing infographic document
        doc_id = active_doc["id"]
        version = await session_service.save_version(
            doc_id,
            infographic_html,
            user_prompt=request.message,
            edit_summary="Regenerated infographic",
            model_used=model_used,
            tokens_used=result.prompt_input_tokens + result.prompt_output_tokens,
            visual_prompt=result.visual_prompt,
        )
        summary = "Regenerated infographic"
    else:
        # New infographic document
        doc_id = await session_service.create_document(session_id, title)
        version = await session_service.save_version(
            doc_id,
            infographic_html,
            user_prompt=request.message,
            edit_summary=f"Created: {title}",
            model_used=model_used,
            tokens_used=result.prompt_input_tokens + result.prompt_output_tokens,
            visual_prompt=result.visual_prompt,
        )
        summary = f"Created: {title}"

    # Track costs for BOTH models
    await cost_tracker.record_usage(
        result.model_prompt,
        result.prompt_input_tokens,
        result.prompt_output_tokens,
    )
    await cost_tracker.record_usage(
        result.model_image, 0, 0, 1  # Image models charge per image, not per token
    )

    await session_service.add_chat_message(
        session_id,
        "assistant",
        summary,
        doc_id,
        "infographic_confirmation",
    )

    yield {"type": "html", "content": infographic_html, "version": version}
    yield {"type": "summary", "content": summary}


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------


@router.post("/api/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    """
    Process a chat message and stream the response via SSE.

    Routes requests to the appropriate model:
    - edit: Claude Sonnet 4.5 (surgical editing via tool_use)
    - create: Gemini 2.5 Pro (streaming, with Claude fallback)
    - image: Gemini image model (raster images)
    """
    from app.services.session_service import session_service
    from app.services.router import classify_request

    # Ensure session exists
    session_id = await session_service.get_or_create_session(session_id)

    # Get active document and current HTML (if any)
    active_doc = await session_service.get_active_document(session_id)
    current_html = None
    if active_doc:
        current_html = await session_service.get_latest_html(
            active_doc["id"]
        )

    # Save user message
    doc_id = active_doc["id"] if active_doc else None
    await session_service.add_chat_message(
        session_id, "user", request.message, doc_id
    )

    # Classify request
    route = await classify_request(request.message, current_html is not None)

    # Override: if active doc is an infographic, route edit/create to infographic
    # so iteration works without requiring the "infographic" keyword every time
    if route in ("edit", "create") and current_html and _is_infographic_doc(current_html):
        logger.info(
            "[ROUTER] Active doc is infographic, overriding to INFOGRAPHIC",
            original_route=route,
            request=request.message[:80],
        )
        route = "infographic"

    async def event_stream():
        try:
            if route == "edit" and current_html:
                handler = _handle_edit(
                    session_service, request, session_id,
                    active_doc, current_html,
                )
            elif route == "create":
                handler = _handle_create(
                    session_service, request, session_id,
                    current_html=current_html,
                )
            elif route == "infographic":
                handler = _handle_infographic(
                    session_service, request, session_id,
                    active_doc, current_html,
                )
            elif route == "image":
                handler = _handle_image(
                    session_service, request, session_id,
                    active_doc, current_html,
                )
            else:
                handler = None

            if handler:
                async for event in handler:
                    yield _sse(event)

            yield _sse({"type": "done"})

        except Exception as e:
            logger.error(
                "Chat error",
                error=str(e),
                error_type=type(e).__name__,
                session_id=session_id[:8],
            )
            user_msg = (
                "Something went wrong. Please try again "
                "or rephrase your request."
            )
            yield _sse({"type": "error", "content": user_msg})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
