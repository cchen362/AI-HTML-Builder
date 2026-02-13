"""Tests for base exporter interface and export options."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest

from app.services.exporters.base import (
    BaseExporter,
    ExportError,
    ExportOptions,
    ExportResult,
)


# ---------------------------------------------------------------------------
# Mock exporter for testing the abstract interface
# ---------------------------------------------------------------------------

class MockExporter(BaseExporter):
    @property
    def format_name(self) -> str:
        return "Mock"

    @property
    def file_extension(self) -> str:
        return "mock"

    @property
    def content_type(self) -> str:
        return "application/mock"

    async def export(self, html_content: str, options: ExportOptions) -> ExportResult:
        return ExportResult(
            content=html_content.encode(),
            content_type=self.content_type,
            file_extension=self.file_extension,
            filename=self.generate_filename(options),
        )


# ---------------------------------------------------------------------------
# BaseExporter tests
# ---------------------------------------------------------------------------

def test_validate_html_valid():
    exporter = MockExporter()
    exporter.validate_html("<!DOCTYPE html><html><body>Test</body></html>")


def test_validate_html_with_html_tag():
    exporter = MockExporter()
    exporter.validate_html("<html><body>Test</body></html>")


def test_validate_html_empty():
    exporter = MockExporter()
    with pytest.raises(ExportError, match="HTML content is empty"):
        exporter.validate_html("")


def test_validate_html_whitespace_only():
    exporter = MockExporter()
    with pytest.raises(ExportError, match="HTML content is empty"):
        exporter.validate_html("   \n  ")


def test_validate_html_invalid():
    exporter = MockExporter()
    with pytest.raises(ExportError, match="Invalid HTML"):
        exporter.validate_html("not html content")


def test_generate_filename_basic():
    exporter = MockExporter()
    options = ExportOptions(document_title="Test Document")
    assert exporter.generate_filename(options) == "Test Document.mock"


def test_generate_filename_sanitization():
    exporter = MockExporter()
    options = ExportOptions(document_title="Test/Doc<>ument|bad")
    filename = exporter.generate_filename(options)
    assert "/" not in filename
    assert "<" not in filename
    assert ">" not in filename
    assert "|" not in filename
    assert filename.endswith(".mock")


def test_generate_filename_empty_title():
    exporter = MockExporter()
    options = ExportOptions(document_title="")
    assert exporter.generate_filename(options) == "document.mock"


# ---------------------------------------------------------------------------
# ExportOptions tests
# ---------------------------------------------------------------------------

def test_export_options_defaults():
    opts = ExportOptions()
    assert opts.document_title == "document"
    assert opts.page_format == "A4"
    assert opts.landscape is False
    assert opts.scale == 1.0
    assert opts.slide_width == 10
    assert opts.slide_height == 7.5
    assert opts.full_page is True
    assert opts.width is None
    assert opts.height is None
    assert opts.custom == {}


def test_export_options_custom_not_shared():
    """Verify default_factory creates independent dicts."""
    opts1 = ExportOptions()
    opts2 = ExportOptions()
    opts1.custom["key"] = "value"
    assert "key" not in opts2.custom


# ---------------------------------------------------------------------------
# Mock exporter export test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_exporter_export():
    exporter = MockExporter()
    html = "<!DOCTYPE html><html><body>Hello</body></html>"
    options = ExportOptions(document_title="test")
    result = await exporter.export(html, options)
    assert result.content == html.encode()
    assert result.content_type == "application/mock"
    assert result.filename == "test.mock"
