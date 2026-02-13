"""Tests for inline HTML export function."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest

from app.services.exporters.base import ExportError, ExportOptions
from app.services.export_service import _export_html

SAMPLE_HTML = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"


@pytest.mark.asyncio
async def test_html_export_basic():
    options = ExportOptions(document_title="test")
    result = await _export_html(SAMPLE_HTML, options)
    assert result.content == SAMPLE_HTML.encode("utf-8")
    assert result.content_type == "text/html"
    assert result.file_extension == "html"
    assert result.filename == "test.html"


@pytest.mark.asyncio
async def test_html_export_metadata():
    options = ExportOptions(document_title="test", include_metadata=True)
    result = await _export_html(SAMPLE_HTML, options)
    assert result.metadata is not None
    assert result.metadata["size_bytes"] == len(SAMPLE_HTML.encode("utf-8"))
    assert result.metadata["encoding"] == "utf-8"


@pytest.mark.asyncio
async def test_html_export_preserves_utf8():
    html = "<!DOCTYPE html><html><body>Hej verden! Ñoño 日本語</body></html>"
    options = ExportOptions(document_title="unicode_test")
    result = await _export_html(html, options)
    assert result.content == html.encode("utf-8")


@pytest.mark.asyncio
async def test_html_export_rejects_empty():
    options = ExportOptions()
    with pytest.raises(ExportError, match="HTML content is empty"):
        await _export_html("", options)


@pytest.mark.asyncio
async def test_html_export_rejects_invalid():
    options = ExportOptions()
    with pytest.raises(ExportError, match="Invalid HTML"):
        await _export_html("just text, not html", options)
