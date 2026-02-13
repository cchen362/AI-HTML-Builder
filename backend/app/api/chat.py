from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import structlog

logger = structlog.get_logger()
router = APIRouter()


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

    # Stream creation
    chunks: list[str] = []
    async for chunk in creator.stream_create(request.message):
        chunks.append(chunk)
        yield {"type": "chunk", "content": chunk}

    full_html = extract_html("".join(chunks))
    title = request.message[:50]

    new_doc_id = await session_service.create_document(
        session_id, title
    )

    # Estimate tokens (streaming doesn't return usage metadata)
    est_input = len(request.message) // 4
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
    """Image: SVG template or Gemini image generation."""
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

    img_fallback = None  # type: ignore[assignment]
    if img_provider:
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
    use_svg, svg_type = img_service.should_use_svg(request.message)

    if use_svg:
        updated_html = img_service.generate_svg_and_embed(
            current_html, svg_type, request.message
        )
        model_used = "svg-template"
        images_generated = 0
    elif img_provider:
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
        images_generated = 1
    else:
        yield {
            "type": "error",
            "content": "Image generation unavailable (no GOOGLE_API_KEY). Only SVG diagrams are supported.",
        }
        return

    version = await session_service.save_version(
        active_doc["id"],
        updated_html,
        user_prompt=request.message,
        edit_summary=f"Added {'SVG diagram' if use_svg else 'image'}",
        model_used=model_used,
        tokens_used=0,
    )

    await cost_tracker.record_usage(
        model_used, 0, 0, images_generated
    )

    await session_service.add_chat_message(
        session_id,
        "assistant",
        f"Added {'SVG diagram' if use_svg else 'image'}",
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
        "content": f"Added {'SVG diagram' if use_svg else 'image'} to document",
    }


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
    - image: Gemini image model or SVG templates
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
                session_id=session_id[:8],
            )
            yield _sse({"type": "error", "content": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
