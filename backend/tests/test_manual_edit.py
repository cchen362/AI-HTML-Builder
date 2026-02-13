"""Tests for manual HTML editing endpoint."""
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
    mock_svc.verify_document_ownership.return_value = True
    with patch("app.api.sessions.session_service", mock_svc):
        yield mock_svc


@pytest.fixture()
def client(mock_session_service):
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_manual_edit_creates_version(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.save_manual_edit.return_value = 2
    resp = client.post(
        "/api/sessions/sess-1/documents/doc-123/manual-edit",
        json={"html_content": "<h1>Manually Edited</h1>"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["version"] == 2
    mock_session_service.save_manual_edit.assert_awaited_once_with(
        "doc-123", "<h1>Manually Edited</h1>"
    )


def test_manual_edit_empty_content_rejected(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    resp = client.post(
        "/api/sessions/sess-1/documents/doc-123/manual-edit",
        json={"html_content": ""},
    )
    assert resp.status_code == 422


def test_manual_edit_missing_content_rejected(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    resp = client.post(
        "/api/sessions/sess-1/documents/doc-123/manual-edit",
        json={},
    )
    assert resp.status_code == 422


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


async def test_save_manual_edit_delegates_to_save_version(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test")
    await service.save_version(doc_id, "<html>v1</html>")

    new_ver = await service.save_manual_edit(doc_id, "<html>manually edited</html>")
    assert new_ver == 2

    ver = await service.get_version(doc_id, 2)
    assert ver is not None
    assert ver["html_content"] == "<html>manually edited</html>"
    assert ver["model_used"] == "manual"
    assert ver["edit_summary"] == "Manual edit"
    assert ver["tokens_used"] == 0
