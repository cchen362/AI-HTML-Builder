"""Tests for the create and image routes in chat.py."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Set required env var before any app imports trigger Settings() validation
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body>
<header><h1>Test</h1></header>
<main><p>Content</p></main>
</body>
</html>"""


def _parse_sse_events(body: str) -> list[dict]:
    """Parse SSE response body into a list of event dicts."""
    events = []
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                pass
    return events


# --- Create route tests ---


@pytest.mark.asyncio
async def test_create_route_streams_and_saves(tmp_path):
    """Test create route: streams HTML chunks, creates doc, saves version."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            mock_anthropic = MagicMock()

            mock_creator = MagicMock()

            async def fake_stream(*args, **kwargs):
                for chunk in ["<!DOCTYPE html>", "<html><body>", "</body></html>"]:
                    yield chunk

            mock_creator.stream_create = fake_stream

            # Patch at source module locations (lazy imports inside function body)
            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini) as MockGemini, \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=mock_anthropic), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML):

                # Override the actual imports inside event_stream
                MockGemini.return_value = mock_gemini

                request = ChatRequest(message="Create a landing page")
                response = await chat("test-session-create", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            event_types = [e["type"] for e in events]

            assert "status" in event_types
            assert "chunk" in event_types
            assert "html" in event_types
            assert "summary" in event_types
            assert "done" in event_types

            html_events = [e for e in events if e["type"] == "html"]
            assert len(html_events) == 1
            assert "version" in html_events[0]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_create_route_fallback_to_claude(tmp_path):
    """When GeminiProvider raises ValueError, falls back to AnthropicProvider."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            mock_anthropic = MagicMock()
            mock_anthropic.model = "claude-sonnet-4-5-20250929"

            mock_creator = MagicMock()

            async def fake_stream(*args, **kwargs):
                yield SAMPLE_HTML

            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", side_effect=ValueError("No key")), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=mock_anthropic), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML):

                request = ChatRequest(message="Create a page")
                response = await chat("test-session-fallback", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)

            # Should succeed (not error)
            assert any(e["type"] == "html" for e in events)
            assert not any(e["type"] == "error" for e in events)

        finally:
            await close_db()


# --- Image route tests ---


@pytest.mark.asyncio
async def test_image_route_svg(tmp_path):
    """Test image route with SVG keyword (flowchart) - zero API cost."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Test Doc")
            await session_service.save_version(doc_id, SAMPLE_HTML)

            from app.api.chat import chat, ChatRequest

            # GeminiImageProvider not available (no API key)
            with patch(
                "app.providers.gemini_image_provider.GeminiImageProvider",
                side_effect=ValueError("no key"),
            ):
                request = ChatRequest(message="Add a flowchart showing the process")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            html_events = [e for e in events if e["type"] == "html"]

            assert len(html_events) == 1
            assert "<svg" in html_events[0]["content"]
            assert "generated-svg" in html_events[0]["content"]

            summary_events = [e for e in events if e["type"] == "summary"]
            assert any("SVG diagram" in e["content"] for e in summary_events)

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_image_route_no_document(tmp_path):
    """Test image route when no document exists - should return error."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            # Force image route by patching at the source module
            with patch("app.services.router.classify_request", return_value="image"):
                request = ChatRequest(message="Add a photo of mountains")
                response = await chat("test-session-no-doc", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            error_events = [e for e in events if e["type"] == "error"]

            assert len(error_events) >= 1
            assert "Create a document first" in error_events[0]["content"]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_image_route_api_image(tmp_path):
    """Test image route with API image generation (non-SVG keyword)."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service
    from app.providers.base import ImageResponse

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Test Doc")
            await session_service.save_version(doc_id, SAMPLE_HTML)

            from app.api.chat import chat, ChatRequest

            mock_img_provider = AsyncMock()
            mock_img_provider.generate_image.return_value = ImageResponse(
                image_bytes=b"\x89PNG" + b"\x00" * 50,
                format="PNG",
                width=1920,
                height=1080,
                model="gemini-image",
                prompt="test",
            )

            with patch(
                "app.providers.gemini_image_provider.GeminiImageProvider",
                return_value=mock_img_provider,
            ):
                request = ChatRequest(message="Add a picture of mountains")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            html_events = [e for e in events if e["type"] == "html"]

            assert len(html_events) == 1
            assert "data:image/png;base64," in html_events[0]["content"]
            assert "generated-image" in html_events[0]["content"]

        finally:
            await close_db()


# --- Edit route still works ---


@pytest.mark.asyncio
async def test_edit_route_unchanged(tmp_path):
    """Verify edit route still functions after create/image additions."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service
    from app.services.editor import EditResult

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Test Doc")
            await session_service.save_version(doc_id, SAMPLE_HTML)

            from app.api.chat import chat, ChatRequest

            mock_result = EditResult(
                html=SAMPLE_HTML.replace("<h1>Test</h1>", "<h1>Updated</h1>"),
                edit_summary="Changed title",
                applied_count=1,
                error_count=0,
                input_tokens=100,
                output_tokens=50,
                model="claude-sonnet-4-5-20250929",
            )

            mock_editor = AsyncMock()
            mock_editor.edit.return_value = mock_result

            with patch("app.services.editor.SurgicalEditor", return_value=mock_editor), \
                 patch("app.providers.anthropic_provider.AnthropicProvider"):
                request = ChatRequest(message="Change the title to Updated")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            html_events = [e for e in events if e["type"] == "html"]

            assert len(html_events) == 1
            assert "<h1>Updated</h1>" in html_events[0]["content"]

        finally:
            await close_db()
