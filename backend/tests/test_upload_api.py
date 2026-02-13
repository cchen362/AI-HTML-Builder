"""Tests for upload API endpoint."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Patch targets — the source module, not the lazy-import consumer
_MOD = "app.utils.file_processors"


@pytest.fixture()
def client():
    """TestClient for the FastAPI app."""
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_upload_txt_file(client: TestClient) -> None:
    mock_result = {
        "filename": "test.txt",
        "file_type": ".txt",
        "content_type": "text",
        "content": "Hello",
        "data_preview": None,
        "row_count": None,
        "columns": None,
    }
    with (
        patch(f"{_MOD}.validate_file"),
        patch(
            f"{_MOD}.process_file",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
        patch(
            f"{_MOD}.generate_upload_prompt",
            return_value="Create a styled HTML document...",
        ),
    ):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["filename"] == "test.txt"
    assert "suggested_prompt" in data


def test_upload_no_filename(client: TestClient) -> None:
    resp = client.post(
        "/api/upload",
        files={"file": ("", b"content", "text/plain")},
    )
    # FastAPI may return 400 (our check) or 422 (framework validation)
    assert resp.status_code in (400, 422)


def test_upload_validation_error(client: TestClient) -> None:
    from app.utils.file_processors import FileProcessingError

    with patch(
        f"{_MOD}.validate_file",
        side_effect=FileProcessingError("File type '.exe' not allowed"),
    ):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.exe", b"data", "application/octet-stream")},
        )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_upload_processing_error(client: TestClient) -> None:
    with (
        patch(f"{_MOD}.validate_file"),
        patch(
            f"{_MOD}.process_file",
            new_callable=AsyncMock,
            side_effect=Exception("kaboom"),
        ),
    ):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"data", "text/plain")},
        )
    assert resp.status_code == 500
    assert "kaboom" in resp.json()["detail"]
