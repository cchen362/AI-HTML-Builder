"""Tests for AI-powered session title generation and related session_service changes (Plan 023 Phase 1)."""

import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure env vars are set before any app imports
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.services.title_generator import (  # noqa: E402
    generate_session_title,
    _reset_client,
)


# ---------------------------------------------------------------------------
# Title generator unit tests (mock Anthropic client)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_title_client():
    """Clear the cached Anthropic client singleton between tests."""
    _reset_client()
    yield
    _reset_client()


def _mock_title_response(title: str) -> MagicMock:
    """Create a mock Anthropic Messages response returning the given title."""
    mock_text_block = MagicMock()
    mock_text_block.text = title

    mock_usage = MagicMock()
    mock_usage.input_tokens = 80
    mock_usage.output_tokens = 8

    mock_resp = MagicMock()
    mock_resp.content = [mock_text_block]
    mock_resp.usage = mock_usage
    return mock_resp


@contextmanager
def _mock_haiku(title: str):
    """Context manager that patches the Anthropic client and cost_tracker."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_title_response(title)
    )
    mock_tracker = AsyncMock()

    with (
        patch(
            "app.services.title_generator._get_client",
            return_value=mock_client,
        ),
        patch("app.services.cost_tracker.cost_tracker", mock_tracker),
    ):
        yield mock_client, mock_tracker


async def test_generate_title_success():
    with _mock_haiku("Q3 Metrics Dashboard") as (client, _tracker):
        result = await generate_session_title("Build me a dashboard for Q3 metrics")
        assert result == "Q3 Metrics Dashboard"
        client.messages.create.assert_called_once()


async def test_generate_title_strips_base64():
    long_b64 = "A" * 200
    msg = f'Check this image data:image/png;base64,{long_b64} and make a report'
    with _mock_haiku("Image Analysis Report") as (client, _tracker):
        await generate_session_title(msg)
        # Verify the base64 was stripped from the message sent to Haiku
        call_args = client.messages.create.call_args
        sent_content = call_args.kwargs["messages"][0]["content"]
        assert long_b64 not in sent_content
        assert "[image]" in sent_content


async def test_generate_title_strips_template_placeholders():
    msg = "Create a professional report about: {{TOPIC}}\n\nSCOPE: quarterly results"
    with _mock_haiku("Quarterly Results Report") as (client, _tracker):
        await generate_session_title(msg)
        call_args = client.messages.create.call_args
        sent_content = call_args.kwargs["messages"][0]["content"]
        assert "{{TOPIC}}" not in sent_content


async def test_generate_title_truncates_long_message():
    msg = "x" * 1000
    with _mock_haiku("Long Session Title") as (client, _tracker):
        await generate_session_title(msg)
        call_args = client.messages.create.call_args
        sent_content = call_args.kwargs["messages"][0]["content"]
        assert len(sent_content) == 500


async def test_generate_title_error_returns_none():
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

    with patch(
        "app.services.title_generator._get_client",
        return_value=mock_client,
    ):
        result = await generate_session_title("Some message")
        assert result is None


async def test_generate_title_empty_input_returns_none():
    # Empty after stripping placeholders
    result = await generate_session_title("{{PLACEHOLDER}}")
    assert result is None


async def test_generate_title_cost_tracked():
    with _mock_haiku("Sales Pitch Deck") as (_client, tracker):
        await generate_session_title("Create a sales pitch")
        tracker.record_usage.assert_called_once_with(
            "claude-haiku-4-5-20251001",  # settings.router_model
            80,  # input_tokens
            8,  # output_tokens
        )


async def test_generate_title_strips_quotes():
    with _mock_haiku('"Q3 Dashboard"') as (_client, _tracker):
        result = await generate_session_title("Build a Q3 dashboard")
        assert result == "Q3 Dashboard"


# ---------------------------------------------------------------------------
# Session service integration tests (title_source + doc_type + infographic_count)
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_and_service(tmp_path):
    """Set up a temp database and session service for testing."""
    db_path = str(tmp_path / "test.db")

    with (
        patch("app.config.settings") as mock_settings,
        patch("app.database.settings") as mock_db_settings,
    ):
        mock_settings.database_path = db_path
        mock_db_settings.database_path = db_path

        import app.database as db_module

        db_module._db = None
        await db_module.init_db()

        from app.services.session_service import SessionService

        service = SessionService()
        yield service
        await db_module.close_db()


async def test_title_source_auto_on_first_message(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Build me a dashboard")

    metadata = await service.get_session_metadata(sid)
    assert metadata.get("title_source") == "auto"
    assert metadata.get("title") == "Build me a dashboard"


async def test_title_source_manual_on_rename(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Build me a dashboard")

    await service.update_session_title(sid, "My Custom Title")

    metadata = await service.get_session_metadata(sid)
    assert metadata.get("title_source") == "manual"
    assert metadata.get("title") == "My Custom Title"


async def test_title_source_ai_on_ai_rename(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Build me a dashboard")

    await service.update_session_title(sid, "Q3 Dashboard", source="ai")

    metadata = await service.get_session_metadata(sid)
    assert metadata.get("title_source") == "ai"
    assert metadata.get("title") == "Q3 Dashboard"


async def test_infographic_count_in_sessions(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")

    # Create 2 regular docs and 1 infographic
    doc1 = await service.create_document(sid, "Doc 1", doc_type="document")
    doc2 = await service.create_document(sid, "Doc 2", doc_type="document")
    doc3 = await service.create_document(sid, "Infographic 1", doc_type="infographic")

    # Save versions so docs are real
    await service.save_version(doc1, "<h1>Doc 1</h1>")
    await service.save_version(doc2, "<h1>Doc 2</h1>")
    await service.save_version(doc3, "<img src='data:image/png;base64,abc'/>")

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 1
    s = sessions[0]
    assert s["doc_count"] == 3
    assert s["infographic_count"] == 1


async def test_infographic_count_zero_when_no_infographics(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.create_document(sid, "Doc 1", doc_type="document")

    sessions = await service.get_user_sessions("user-1")
    assert sessions[0]["infographic_count"] == 0


async def test_title_source_in_sessions_response(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Build me a dashboard")

    sessions = await service.get_user_sessions("user-1")
    assert sessions[0]["title_source"] == "auto"

    await service.update_session_title(sid, "Custom", source="manual")

    sessions = await service.get_user_sessions("user-1")
    assert sessions[0]["title_source"] == "manual"
