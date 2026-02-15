"""Tests for version restore functionality."""
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
    with (
        patch("app.api.sessions.session_service", mock_svc),
        patch("app.api.sessions._require_session_ownership", new_callable=AsyncMock),
    ):
        yield mock_svc


@pytest.fixture()
def client(mock_session_service):
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_restore_version_endpoint_success(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.restore_version.return_value = 3
    resp = client.post("/api/sessions/sess-1/documents/doc-123/versions/1/restore")
    assert resp.status_code == 200
    assert resp.json()["version"] == 3
    mock_session_service.restore_version.assert_awaited_once_with("doc-123", 1)


def test_restore_version_endpoint_not_found(
    client: TestClient, mock_session_service: AsyncMock
) -> None:
    mock_session_service.restore_version.side_effect = ValueError(
        "Version 999 not found"
    )
    resp = client.post("/api/sessions/sess-1/documents/doc-123/versions/999/restore")
    assert resp.status_code == 404
    assert "999" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Service-level tests (real DB)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def db_and_service(tmp_path):
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


async def test_restore_version_creates_new_version(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test")
    await service.save_version(doc_id, "<html><body>v1</body></html>")
    await service.save_version(doc_id, "<html><body>v2</body></html>")

    new_ver = await service.restore_version(doc_id, 1)
    assert new_ver == 3

    restored = await service.get_version(doc_id, 3)
    assert restored is not None
    assert restored["html_content"] == "<html><body>v1</body></html>"
    assert restored["edit_summary"] == "Restored from version 1"
    assert restored["model_used"] == "restore"


async def test_restore_nonexistent_version_raises(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test")
    await service.save_version(doc_id, "<html>v1</html>")

    with pytest.raises(ValueError, match="Version 999 not found"):
        await service.restore_version(doc_id, 999)


async def test_restore_preserves_original_version(db_and_service) -> None:
    service = db_and_service
    sid = await service.create_session()
    doc_id = await service.create_document(sid, "Test")
    await service.save_version(doc_id, "<html>original</html>")
    await service.save_version(doc_id, "<html>edited</html>")

    await service.restore_version(doc_id, 1)

    # Original v1 still intact
    v1 = await service.get_version(doc_id, 1)
    assert v1 is not None
    assert v1["html_content"] == "<html>original</html>"

    # v2 still intact
    v2 = await service.get_version(doc_id, 2)
    assert v2 is not None
    assert v2["html_content"] == "<html>edited</html>"

    # Latest is the restored v3
    latest = await service.get_latest_html(doc_id)
    assert latest == "<html>original</html>"
