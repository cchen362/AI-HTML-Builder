"""Tests for infographic export guard in export_service."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.exporters.base import ExportError, ExportOptions

# Sample infographic HTML (matches is_infographic_html detection)
INFOGRAPHIC_HTML = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    '<style>*{margin:0}body{background:#0a0a0f;display:flex;'
    'justify-content:center;align-items:center;min-height:100vh}'
    'img{max-width:100%;height:auto}</style></head>'
    '<body><img src="data:image/png;base64,' + 'A' * 200 + '" alt="test"/></body></html>'
)


@pytest.fixture
def mock_session_service():
    """Mock session_service to return infographic HTML."""
    mock_svc = AsyncMock()
    mock_svc.get_latest_html.return_value = INFOGRAPHIC_HTML
    with patch("app.services.export_service.session_service", mock_svc):
        yield mock_svc


@pytest.mark.asyncio
async def test_infographic_pdf_export_blocked(mock_session_service):
    """PDF export of infographic should raise ExportError."""
    from app.services.export_service import export_document

    with pytest.raises(ExportError, match="can only be exported as PNG or HTML"):
        await export_document("doc-123", "pdf")


@pytest.mark.asyncio
async def test_infographic_pptx_export_blocked(mock_session_service):
    """PPTX export of infographic should raise ExportError."""
    from app.services.export_service import export_document

    with pytest.raises(ExportError, match="can only be exported as PNG or HTML"):
        await export_document("doc-123", "pptx")


@pytest.mark.asyncio
async def test_infographic_png_export_uses_direct_extraction(mock_session_service):
    """PNG export of infographic should use direct base64 extraction, not Playwright."""
    from app.services.export_service import export_document

    result = await export_document(
        "doc-123", "png", options=ExportOptions(document_title="test-info")
    )
    assert result.content_type == "image/png"
    assert result.metadata is not None
    assert result.metadata["source"] == "direct-base64-extraction"
