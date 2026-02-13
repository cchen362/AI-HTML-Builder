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


# --- Transformation context tests (Plan 016) ---


@pytest.mark.asyncio
async def test_create_route_with_existing_html_passes_context(tmp_path):
    """When route=create and HTML exists (transformation), current_html is passed to creator."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            # Create session with existing document
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Slides")
            await session_service.save_version(doc_id, SAMPLE_HTML)

            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            captured_calls: list = []

            async def fake_stream(msg, template_content=None):
                captured_calls.append({"msg": msg, "template_content": template_content})
                yield SAMPLE_HTML

            mock_creator = MagicMock()
            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=MagicMock()), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML), \
                 patch("app.services.router.classify_request", new_callable=AsyncMock, return_value="create"):

                request = ChatRequest(message="Turn this into a stakeholder brief")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            # Verify template_content was passed (existing HTML as context)
            assert len(captured_calls) == 1
            assert captured_calls[0]["template_content"] is not None
            assert "<!DOCTYPE html>" in captured_calls[0]["template_content"]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_create_route_without_html_no_context(tmp_path):
    """When route=create and no HTML exists (fresh creation), template_content is None."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            captured_calls: list = []

            async def fake_stream(msg, template_content=None):
                captured_calls.append({"msg": msg, "template_content": template_content})
                yield SAMPLE_HTML

            mock_creator = MagicMock()
            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=MagicMock()), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML):

                request = ChatRequest(message="Create a landing page")
                response = await chat("test-session-no-context", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            # Verify template_content is None (no existing doc)
            assert len(captured_calls) == 1
            assert captured_calls[0]["template_content"] is None

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_create_route_strips_base64_from_context(tmp_path):
    """When existing HTML contains base64 images, base64 payload is stripped but
    <img> tag and alt text are preserved in context passed to creator."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service

    html_with_image = (
        '<!DOCTYPE html><html lang="en"><head><title>Test</title></head>'
        '<body><main><p>Content</p>'
        '<img src="data:image/png;base64,' + "A" * 200 + '" '
        'alt="Revenue chart" style="max-width:100%"/>'
        '</main></body></html>'
    )

    db_path = tmp_path / "test.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Slides")
            await session_service.save_version(doc_id, html_with_image)

            from app.api.chat import chat, ChatRequest

            mock_gemini = MagicMock()
            mock_gemini.model = "gemini-2.5-pro"

            captured_calls: list = []

            async def fake_stream(msg, template_content=None):
                captured_calls.append({"msg": msg, "template_content": template_content})
                yield SAMPLE_HTML

            mock_creator = MagicMock()
            mock_creator.stream_create = fake_stream

            with patch("app.providers.gemini_provider.GeminiProvider", return_value=mock_gemini), \
                 patch("app.providers.anthropic_provider.AnthropicProvider", return_value=MagicMock()), \
                 patch("app.services.creator.DocumentCreator", return_value=mock_creator), \
                 patch("app.services.creator.extract_html", return_value=SAMPLE_HTML), \
                 patch("app.services.router.classify_request", new_callable=AsyncMock, return_value="create"):

                request = ChatRequest(message="Turn this into a stakeholder brief")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            assert len(captured_calls) == 1
            ctx = captured_calls[0]["template_content"]

            # Base64 payload should be stripped
            assert "AAAA" not in ctx
            # But the <img> tag and alt text should be preserved
            assert 'alt="Revenue chart"' in ctx
            assert "[image-removed]" in ctx
            # The data URI prefix should still be there
            assert "data:image/png;base64," in ctx

        finally:
            await close_db()


# --- Image route tests ---


@pytest.mark.asyncio
async def test_image_route_no_provider_returns_error(tmp_path):
    """Image route with no provider returns error (SVG branch removed)."""
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
            ), patch(
                "app.services.router.classify_request",
                new_callable=AsyncMock,
                return_value="image",
            ):
                request = ChatRequest(message="Add a photo of mountains")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            error_events = [e for e in events if e["type"] == "error"]

            assert len(error_events) >= 1
            assert "unavailable" in error_events[0]["content"]

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
            with patch("app.services.router.classify_request", new_callable=AsyncMock, return_value="image"):
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
            ), patch(
                "app.services.router.classify_request",
                new_callable=AsyncMock,
                return_value="image",
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


# --- Title extraction tests (Plan 015) ---


def test_template_title_strips_placeholder():
    from app.api.chat import _extract_title

    msg = "Create an engaging slide presentation about: {{TOPIC}}\n\nMy content"
    title = _extract_title(msg)
    assert "{{" not in title
    assert "slide presentation" in title.lower()


def test_template_title_strips_brd_placeholder():
    from app.api.chat import _extract_title

    msg = "Create a Business Requirements Document (BRD) for: {{PROJECT_OR_INITIATIVE}}\n\nDetails"
    title = _extract_title(msg)
    assert "{{" not in title
    assert "BRD" in title or "Business Requirements" in title


def test_normal_message_title():
    from app.api.chat import _extract_title

    msg = "Create a landing page for my startup"
    assert _extract_title(msg) == "Create a landing page for my startup"


def test_long_message_title_truncated():
    from app.api.chat import _extract_title

    msg = "A" * 200
    assert len(_extract_title(msg)) <= 50


def test_multiline_message_uses_first_line():
    from app.api.chat import _extract_title

    msg = "Create a dashboard\n\nWith lots of charts and data"
    assert _extract_title(msg) == "Create a dashboard"


# --- Edit route still works ---


# --- Infographic route tests (Plan 018) ---


@pytest.mark.asyncio
async def test_infographic_route_creates_document(tmp_path):
    """Infographic route should generate image, wrap in HTML, create doc tab."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.infographic_service import InfographicResult

    db_path = tmp_path / "test_infographic.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            mock_result = InfographicResult(
                image_bytes=b"\x89PNG" + b"\x00" * 50,
                image_format="PNG",
                visual_prompt="A detailed infographic about revenue...",
                model_prompt="gemini-2.5-pro",
                model_image="gemini-3-pro-image-preview",
                prompt_input_tokens=500,
                prompt_output_tokens=200,
            )

            mock_service_instance = AsyncMock()
            mock_service_instance.generate.return_value = mock_result

            with patch(
                "app.services.infographic_service.InfographicService",
                return_value=mock_service_instance,
            ), patch(
                "app.providers.gemini_provider.GeminiProvider",
            ), patch(
                "app.providers.gemini_image_provider.GeminiImageProvider",
            ), patch(
                "app.services.router.classify_request",
                new_callable=AsyncMock,
                return_value="infographic",
            ):
                request = ChatRequest(message="Create an infographic about revenue")
                response = await chat("test-session-infographic", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            event_types = [e["type"] for e in events]

            assert "status" in event_types
            assert "html" in event_types
            assert "summary" in event_types
            assert "done" in event_types

            # HTML event should contain base64 image
            html_events = [e for e in events if e["type"] == "html"]
            assert len(html_events) == 1
            assert "data:image/png;base64," in html_events[0]["content"]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_infographic_route_no_google_key_returns_error(tmp_path):
    """Infographic route without GOOGLE_API_KEY should return error."""
    from app.database import init_db, close_db
    from app.config import settings

    db_path = tmp_path / "test_infographic_nokey.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            from app.api.chat import chat, ChatRequest

            with patch(
                "app.providers.gemini_provider.GeminiProvider",
                side_effect=ValueError("No key"),
            ), patch(
                "app.services.router.classify_request",
                new_callable=AsyncMock,
                return_value="infographic",
            ):
                request = ChatRequest(message="Create an infographic about revenue")
                response = await chat("test-session-infographic-nokey", request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            error_events = [e for e in events if e["type"] == "error"]

            assert len(error_events) >= 1
            assert "unavailable" in error_events[0]["content"]

        finally:
            await close_db()


@pytest.mark.asyncio
async def test_infographic_iteration_override(tmp_path):
    """Edit/create on an infographic doc should override route to infographic."""
    from app.database import init_db, close_db
    from app.config import settings
    from app.services.session_service import session_service
    from app.services.infographic_service import InfographicResult, wrap_infographic_html

    db_path = tmp_path / "test_infographic_iter.db"
    with patch.object(settings, "database_path", str(db_path)):
        await init_db()

        try:
            sid = await session_service.create_session()
            doc_id = await session_service.create_document(sid, "Infographic")

            # Save an infographic doc (minimal HTML with base64 <img>)
            infographic_html = wrap_infographic_html(
                b"\x89PNG" + b"\x00" * 50, "PNG", "Test infographic"
            )
            await session_service.save_version(doc_id, infographic_html)

            from app.api.chat import chat, ChatRequest

            mock_result = InfographicResult(
                image_bytes=b"\x89PNG" + b"\x00" * 60,
                image_format="PNG",
                visual_prompt="Updated visual prompt...",
                model_prompt="gemini-2.5-pro",
                model_image="gemini-3-pro-image-preview",
                prompt_input_tokens=500,
                prompt_output_tokens=200,
            )

            mock_service_instance = AsyncMock()
            mock_service_instance.generate.return_value = mock_result

            # Router returns "edit" — but the override should send to infographic
            mock_classify = AsyncMock(return_value="edit")
            with patch(
                "app.services.infographic_service.InfographicService",
                return_value=mock_service_instance,
            ), patch(
                "app.providers.gemini_provider.GeminiProvider",
            ), patch(
                "app.providers.gemini_image_provider.GeminiImageProvider",
            ), patch(
                "app.services.router.classify_request",
                mock_classify,
            ), patch(
                "app.services.cost_tracker.cost_tracker",
                AsyncMock(),
            ):
                request = ChatRequest(message="make it less prose and bigger text")
                response = await chat(sid, request)

                body = ""
                async for chunk in response.body_iterator:
                    body += chunk

            events = _parse_sse_events(body)
            html_events = [e for e in events if e["type"] == "html"]

            # Should have generated a new infographic, not tried to edit
            assert len(html_events) == 1
            assert "data:image/png;base64," in html_events[0]["content"]

            # InfographicService.generate should have been called
            mock_service_instance.generate.assert_called_once()

        finally:
            await close_db()


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
                 patch("app.providers.anthropic_provider.AnthropicProvider"), \
                 patch("app.services.router.classify_request", new_callable=AsyncMock, return_value="edit"):
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
