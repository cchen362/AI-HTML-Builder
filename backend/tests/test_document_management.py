"""Tests for document rename and delete functionality."""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# API-level tests (mocked service)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session_service():
    mock_svc = AsyncMock()
    with patch("app.api.sessions.session_service", mock_svc):
        yield mock_svc


@pytest.fixture()
def client(mock_session_service):
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


# --- Rename ---


def test_rename_document_success(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.rename_document.return_value = True
    resp = client.patch(
        "/api/documents/doc-123",
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_session_service.rename_document.assert_awaited_once_with(
        "doc-123", "New Title"
    )


def test_rename_document_not_found(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.rename_document.return_value = False
    resp = client.patch(
        "/api/documents/doc-999",
        json={"title": "New Title"},
    )
    assert resp.status_code == 404


def test_rename_document_empty_title_rejected(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    resp = client.patch(
        "/api/documents/doc-123",
        json={"title": ""},
    )
    assert resp.status_code == 422


# --- Delete ---


def test_delete_document_success(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.delete_document.return_value = True
    resp = client.delete("/api/sessions/sess-1/documents/doc-123")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_session_service.delete_document.assert_awaited_once_with(
        "sess-1", "doc-123"
    )


def test_delete_last_document_blocked(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.delete_document.return_value = False
    resp = client.delete("/api/sessions/sess-1/documents/doc-123")
    assert resp.status_code == 400
    assert "Cannot delete" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Service-level tests (real DB)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def db_and_service(tmp_path):
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


async def test_rename_document_service(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Original")
    result = await service.rename_document(doc_id, "Renamed")
    assert result is True

    docs = await service.get_session_documents(sid)
    assert docs[0]["title"] == "Renamed"


async def test_rename_nonexistent_document(db_and_service) -> None:
    service = db_and_service
    result = await service.rename_document("nonexistent-id", "Title")
    assert result is False


async def test_delete_document_activates_another(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc1 = await service.create_document(sid, "First")
    doc2 = await service.create_document(sid, "Second")

    # doc2 is active (last created)
    active = await service.get_active_document(sid)
    assert active is not None
    assert active["id"] == doc2

    # Delete active doc2 — doc1 should become active
    result = await service.delete_document(sid, doc2)
    assert result is True

    active = await service.get_active_document(sid)
    assert active is not None
    assert active["id"] == doc1


async def test_delete_last_document_blocked(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Only")
    result = await service.delete_document(sid, doc_id)
    assert result is False

    # Document still exists
    docs = await service.get_session_documents(sid)
    assert len(docs) == 1


async def test_delete_nullifies_chat_messages(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc1 = await service.create_document(sid, "First")
    doc2 = await service.create_document(sid, "Second")

    # Add chat message linked to doc1
    await service.add_chat_message(sid, "user", "hello", document_id=doc1)

    # Delete doc1
    result = await service.delete_document(sid, doc1)
    assert result is True

    # Chat message still exists but document_id is NULL
    messages = await service.get_chat_history(sid)
    assert len(messages) == 1
    assert messages[0]["document_id"] is None
