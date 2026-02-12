from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import structlog

logger = structlog.get_logger()
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    document_id: str | None = None  # If None, uses active document


@router.post("/api/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    """
    Process a chat message and stream the response via SSE.

    Routes requests to the appropriate model:
    - edit: Claude Sonnet 4.5 (surgical editing via tool_use)
    - create: Gemini 2.5 Pro (Plan 003)
    - image: Nano Banana Pro (Plan 003)
    """
    from app.services.session_service import session_service
    from app.services.router import classify_request
    from app.services.editor import SurgicalEditor
    from app.providers.anthropic_provider import AnthropicProvider
    from app.services.cost_tracker import cost_tracker

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
    route = classify_request(request.message, current_html is not None)

    async def event_stream():
        try:
            if route == "edit" and current_html:
                # SURGICAL EDIT via Claude tool_use
                yield (
                    f"data: {json.dumps({'type': 'status', 'content': 'Editing...'})}\n\n"
                )

                editor = SurgicalEditor(AnthropicProvider())
                chat_history = await session_service.get_chat_history(
                    session_id, limit=8
                )

                result = await editor.edit(
                    current_html, request.message, chat_history
                )

                # Save new version
                version = await session_service.save_version(
                    active_doc["id"],  # type: ignore[index]
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
                    active_doc["id"],  # type: ignore[index]
                    "edit_confirmation",
                )

                yield (
                    f"data: {json.dumps({'type': 'html', 'content': result.html, 'version': version})}\n\n"
                )
                yield (
                    f"data: {json.dumps({'type': 'summary', 'content': result.edit_summary})}\n\n"
                )

            elif route == "create":
                # NEW DOCUMENT via Gemini (implemented in Plan 003)
                yield (
                    f"data: {json.dumps({'type': 'status', 'content': 'Creating document...'})}\n\n"
                )
                yield (
                    f"data: {json.dumps({'type': 'error', 'content': 'Creation not yet implemented'})}\n\n"
                )

            elif route == "image":
                # IMAGE generation via Nano Banana Pro (implemented in Plan 003)
                yield (
                    f"data: {json.dumps({'type': 'status', 'content': 'Generating image...'})}\n\n"
                )
                yield (
                    f"data: {json.dumps({'type': 'error', 'content': 'Image generation not yet implemented'})}\n\n"
                )

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(
                "Chat error",
                error=str(e),
                session_id=session_id[:8],
            )
            yield (
                f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
