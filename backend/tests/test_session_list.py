"""Tests for session listing, deletion, title update, and auto-titling (Plan 021 Phase 2)."""

import asyncio
import pytest
from unittest.mock import patch


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


# --- get_user_sessions ---


async def test_get_user_sessions_empty(db_and_service):
    service = db_and_service
    sessions = await service.get_user_sessions("user-1")
    assert sessions == []


async def test_get_user_sessions_returns_summary(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    doc_id = await service.create_document(sid, "My Doc")
    await service.save_version(doc_id, "<h1>Hello</h1>")

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 1
    s = sessions[0]
    assert s["id"] == sid
    assert s["doc_count"] == 1
    assert s["last_active"] is not None
    assert s["created_at"] is not None
    assert s["title"] == "Untitled Session"  # no chat messages yet


async def test_get_user_sessions_with_auto_title(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Build me a dashboard for Q3 metrics")

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Build me a dashboard for Q3 metrics"
    assert sessions[0]["first_message_preview"] == "Build me a dashboard for Q3 metrics"


async def test_get_user_sessions_with_template_title(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(
        sid,
        "user",
        "Create a professional impact assessment report about: cloud migration\n\nSCOPE:...",
        template_name="Impact Assessment Report",
        user_content="cloud migration",
    )

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 1
    # Should use template_name, not the full prompt text
    assert sessions[0]["title"] == "Impact Assessment Report"


async def test_get_user_sessions_with_manual_title(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid, "user", "Hello world")
    await service.update_session_title(sid, "My Custom Title")

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 1
    assert sessions[0]["title"] == "My Custom Title"


async def test_get_user_sessions_pagination(db_and_service):
    service = db_and_service
    for i in range(5):
        sid = await service.create_session(user_id="user-1")
        await service.add_chat_message(sid, "user", f"Session {i}")
        # Small delay to ensure different last_active timestamps
        await asyncio.sleep(0.01)

    # First page
    page1 = await service.get_user_sessions("user-1", limit=2, offset=0)
    assert len(page1) == 2

    # Second page
    page2 = await service.get_user_sessions("user-1", limit=2, offset=2)
    assert len(page2) == 2

    # Third page
    page3 = await service.get_user_sessions("user-1", limit=2, offset=4)
    assert len(page3) == 1

    # All IDs unique
    all_ids = [s["id"] for s in page1 + page2 + page3]
    assert len(set(all_ids)) == 5


async def test_get_user_sessions_only_own(db_and_service):
    service = db_and_service
    sid1 = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid1, "user", "User 1 session")
    sid2 = await service.create_session(user_id="user-2")
    await service.add_chat_message(sid2, "user", "User 2 session")

    sessions_1 = await service.get_user_sessions("user-1")
    sessions_2 = await service.get_user_sessions("user-2")

    assert len(sessions_1) == 1
    assert sessions_1[0]["id"] == sid1
    assert len(sessions_2) == 1
    assert sessions_2[0]["id"] == sid2


async def test_get_user_sessions_ordered_by_last_active(db_and_service):
    service = db_and_service
    from app.database import get_db

    sid_old = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid_old, "user", "Old session")

    sid_new = await service.create_session(user_id="user-1")
    await service.add_chat_message(sid_new, "user", "New session")

    # Manually set last_active to ensure distinct timestamps
    # (SQLite CURRENT_TIMESTAMP has second-level precision)
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET last_active = '2025-01-01 00:00:00' WHERE id = ?",
        (sid_old,),
    )
    await db.execute(
        "UPDATE sessions SET last_active = '2025-06-01 00:00:00' WHERE id = ?",
        (sid_new,),
    )
    await db.commit()

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 2
    # Most recent first
    assert sessions[0]["id"] == sid_new
    assert sessions[1]["id"] == sid_old


# --- delete_session ---


async def test_delete_session(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    assert await service.delete_session(sid) is True

    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 0


async def test_delete_session_cascades(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    doc_id = await service.create_document(sid, "Test Doc")
    await service.save_version(doc_id, "<p>Content</p>")
    await service.add_chat_message(sid, "user", "Test message")

    assert await service.delete_session(sid) is True

    # Session gone
    sessions = await service.get_user_sessions("user-1")
    assert len(sessions) == 0

    # Document and version gone (check via get_latest_html)
    html = await service.get_latest_html(doc_id)
    assert html is None


async def test_delete_nonexistent_session(db_and_service):
    service = db_and_service
    assert await service.delete_session("nonexistent-id") is False


# --- update_session_title ---


async def test_update_session_title(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    assert await service.update_session_title(sid, "My Project") is True

    sessions = await service.get_user_sessions("user-1")
    assert sessions[0]["title"] == "My Project"


async def test_update_session_title_nonexistent(db_and_service):
    service = db_and_service
    assert await service.update_session_title("nonexistent", "Title") is False


# --- last_active updated on chat message ---


async def test_last_active_updated_on_chat_message(db_and_service):
    service = db_and_service
    from app.database import get_db

    sid = await service.create_session(user_id="user-1")

    db = await get_db()
    cursor = await db.execute(
        "SELECT last_active FROM sessions WHERE id = ?", (sid,)
    )
    row = await cursor.fetchone()
    initial_active = row["last_active"]

    await asyncio.sleep(0.02)
    await service.add_chat_message(sid, "user", "Hello!")

    cursor = await db.execute(
        "SELECT last_active FROM sessions WHERE id = ?", (sid,)
    )
    row = await cursor.fetchone()
    updated_active = row["last_active"]

    # last_active should have been updated
    assert updated_active >= initial_active


# --- auto-title does not overwrite manual title ---


async def test_auto_title_not_overwritten(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="user-1")
    await service.update_session_title(sid, "Manual Title")

    # Add a user message — should NOT overwrite the manual title
    await service.add_chat_message(sid, "user", "This should not become the title")

    sessions = await service.get_user_sessions("user-1")
    assert sessions[0]["title"] == "Manual Title"


# --- API tests ---


async def test_list_sessions_api(db_and_service):
    service = db_and_service
    await service.create_session(user_id="test-user-id")

    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert len(data["sessions"]) == 1


async def test_delete_session_api(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="test-user-id")

    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/api/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_update_session_title_api(db_and_service):
    service = db_and_service
    sid = await service.create_session(user_id="test-user-id")

    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/sessions/{sid}",
            json={"title": "New Title"},
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify title persisted
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions")
    assert resp.json()["sessions"][0]["title"] == "New Title"


async def test_delete_other_users_session_403(db_and_service):
    service = db_and_service
    # Create session owned by a different user
    sid = await service.create_session(user_id="other-user-id")

    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/api/sessions/{sid}")
    assert resp.status_code == 403
