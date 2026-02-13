"""Tests for export API endpoints."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.exporters.base import ExportError, ExportResult


@pytest.fixture
def mock_export_fns():
    """Patch export functions at the API module level."""
    with (
        patch("app.api.export.export_document", new_callable=AsyncMock) as mock_export,
        patch("app.api.export.list_available_formats") as mock_formats,
    ):
        mock_formats.return_value = {
            "html": "HTML",
            "pdf": "PDF",
            "pptx": "PowerPoint",
            "png": "PNG",
        }
        yield mock_export, mock_formats


@pytest.fixture
def client(mock_export_fns):
    """TestClient with mocked export functions."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _html_result() -> ExportResult:
    return ExportResult(
        content=b"<html>test</html>",
        content_type="text/html",
        file_extension="html",
        filename="test.html",
    )


def _pdf_result() -> ExportResult:
    return ExportResult(
        content=b"%PDF-1.4",
        content_type="application/pdf",
        file_extension="pdf",
        filename="test.pdf",
    )


# ---------------------------------------------------------------------------
# HTML export endpoint
# ---------------------------------------------------------------------------

def test_export_html_returns_200(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.return_value = _html_result()
    resp = client.post("/api/export/doc-123/html", params={"title": "test"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_html_with_version(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.return_value = _html_result()
    resp = client.post("/api/export/doc-123/html", params={"version": 2})
    assert resp.status_code == 200
    call_kwargs = mock_export.call_args[1]
    assert call_kwargs["version"] == 2


# ---------------------------------------------------------------------------
# PDF export endpoint
# ---------------------------------------------------------------------------

def test_export_pdf_returns_200(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.return_value = _pdf_result()
    resp = client.post("/api/export/doc-123/pdf")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_export_returns_400_on_export_error(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.side_effect = ExportError("Document not found")
    resp = client.post("/api/export/doc-123/html")
    assert resp.status_code == 400
    assert "Document not found" in resp.json()["detail"]


def test_export_returns_500_on_unexpected_error(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.side_effect = RuntimeError("unexpected")
    resp = client.post("/api/export/doc-123/html")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Export failed"


# ---------------------------------------------------------------------------
# List formats endpoint
# ---------------------------------------------------------------------------

def test_list_formats(client, mock_export_fns):
    resp = client.get("/api/export/formats")
    assert resp.status_code == 200
    data = resp.json()
    assert "formats" in data
    assert data["formats"]["html"] == "HTML"
    assert data["formats"]["pdf"] == "PDF"
    assert data["formats"]["pptx"] == "PowerPoint"
    assert data["formats"]["png"] == "PNG"


# ---------------------------------------------------------------------------
# Content-Disposition tests
# ---------------------------------------------------------------------------

def test_content_disposition_has_filename(client, mock_export_fns):
    mock_export, _mock_formats = mock_export_fns
    mock_export.return_value = _html_result()
    resp = client.post("/api/export/doc-123/html", params={"title": "myfile"})
    assert 'filename="test.html"' in resp.headers.get("content-disposition", "")
