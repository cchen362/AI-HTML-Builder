import pytest
from unittest.mock import patch


@pytest.fixture
async def db_and_service(tmp_path):
    """Set up a temp database and session service for testing."""
    db_path = str(tmp_path / "test.db")

    with patch("app.config.settings") as mock_settings:
        mock_settings.database_path = db_path

        import app.database as db_module

        db_module._db = None
        await db_module.init_db()

        from app.services.session_service import SessionService

        service = SessionService()
        yield service
        await db_module.close_db()


@pytest.mark.asyncio
async def test_create_session(db_and_service):
    service = db_and_service
    session_id = await service.create_session()
    assert session_id
    assert len(session_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_get_or_create_existing(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    result = await service.get_or_create_session(sid)
    assert result == sid


@pytest.mark.asyncio
async def test_get_or_create_new(db_and_service):
    service = db_and_service
    result = await service.get_or_create_session("nonexistent-id")
    assert result != "nonexistent-id"
    assert len(result) == 36


@pytest.mark.asyncio
async def test_create_document(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test Doc")
    assert doc_id
    assert len(doc_id) == 36


@pytest.mark.asyncio
async def test_get_active_document(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test Doc")

    active = await service.get_active_document(sid)
    assert active is not None
    assert active["id"] == doc_id
    assert active["title"] == "Test Doc"
    assert active["is_active"] == 1


@pytest.mark.asyncio
async def test_create_document_deactivates_previous(db_and_service):
    service = db_and_service
    sid = await service.create_session()

    doc1 = await service.create_document(sid, "Doc 1")
    doc2 = await service.create_document(sid, "Doc 2")

    active = await service.get_active_document(sid)
    assert active["id"] == doc2

    docs = await service.get_session_documents(sid)
    assert len(docs) == 2


@pytest.mark.asyncio
async def test_switch_document(db_and_service):
    service = db_and_service
    sid = await service.create_session()

    doc1 = await service.create_document(sid, "Doc 1")
    doc2 = await service.create_document(sid, "Doc 2")

    success = await service.switch_document(sid, doc1)
    assert success is True

    active = await service.get_active_document(sid)
    assert active["id"] == doc1


@pytest.mark.asyncio
async def test_switch_nonexistent_document(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    success = await service.switch_document(sid, "nonexistent")
    assert success is False


@pytest.mark.asyncio
async def test_save_and_get_version(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    v1 = await service.save_version(
        doc_id, "<h1>Hello</h1>", user_prompt="Make a heading"
    )
    assert v1 == 1

    v2 = await service.save_version(
        doc_id, "<h1>World</h1>", user_prompt="Change title"
    )
    assert v2 == 2


@pytest.mark.asyncio
async def test_get_latest_html(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    await service.save_version(doc_id, "<h1>V1</h1>")
    await service.save_version(doc_id, "<h1>V2</h1>")

    html = await service.get_latest_html(doc_id)
    assert html == "<h1>V2</h1>"


@pytest.mark.asyncio
async def test_get_latest_html_no_versions(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    html = await service.get_latest_html(doc_id)
    assert html is None


@pytest.mark.asyncio
async def test_get_version(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    await service.save_version(doc_id, "<h1>V1</h1>", user_prompt="First")
    ver = await service.get_version(doc_id, 1)
    assert ver is not None
    assert ver["html_content"] == "<h1>V1</h1>"
    assert ver["user_prompt"] == "First"


@pytest.mark.asyncio
async def test_get_version_history(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    await service.save_version(doc_id, "<h1>V1</h1>")
    await service.save_version(doc_id, "<h1>V2</h1>")
    await service.save_version(doc_id, "<h1>V3</h1>")

    history = await service.get_version_history(doc_id)
    assert len(history) == 3
    # Ordered DESC
    assert history[0]["version"] == 3
    assert history[2]["version"] == 1


@pytest.mark.asyncio
async def test_chat_messages(db_and_service):
    service = db_and_service
    sid = await service.create_session()

    await service.add_chat_message(sid, "user", "Hello")
    await service.add_chat_message(sid, "assistant", "Hi there")

    messages = await service.get_chat_history(sid)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_messages_with_document(db_and_service):
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid)

    await service.add_chat_message(
        sid, "user", "Edit heading", document_id=doc_id
    )

    messages = await service.get_chat_history(sid)
    assert len(messages) == 1
    assert messages[0]["document_id"] == doc_id


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(db_and_service):
    service = db_and_service
    from app.database import get_db

    # Create a session and manually backdate it
    sid = await service.create_session()
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET last_active = datetime('now', '-48 hours') WHERE id = ?",
        (sid,),
    )
    await db.commit()

    deleted = await service.cleanup_expired_sessions(timeout_hours=24)
    assert deleted == 1
