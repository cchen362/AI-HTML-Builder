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
from app.utils.export_utils import sanitize_title


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
    assert exporter.generate_filename(options) == "Test-Document.mock"


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
# sanitize_title tests (shared utility)
# ---------------------------------------------------------------------------

def test_sanitize_title_spaces_to_hyphens():
    assert sanitize_title("My Cool Document") == "My-Cool-Document"


def test_sanitize_title_special_chars_replaced():
    # / becomes _, <> becomes __ which collapses to _
    assert sanitize_title("Hello/World<>Test") == "Hello_World_Test"


def test_sanitize_title_collapses_double_hyphens():
    assert sanitize_title("one - two - three") == "one-two-three"


def test_sanitize_title_collapses_double_underscores():
    assert sanitize_title("a///b") == "a_b"


def test_sanitize_title_truncates_at_60_chars():
    long_title = "A " + "word " * 20  # well over 60 chars
    result = sanitize_title(long_title)
    assert len(result) <= 60


def test_sanitize_title_truncates_at_word_boundary():
    # 70 chars with hyphens — should truncate at a separator before 60
    title = "alpha-bravo-charlie-delta-echo-foxtrot-golf-hotel-india-juliet-kilo-lima"
    result = sanitize_title(title)
    assert len(result) <= 60
    assert not result.endswith("-")
    assert not result.endswith("_")


def test_sanitize_title_strips_trailing_separators():
    assert sanitize_title("hello-") == "hello"
    assert sanitize_title("hello_") == "hello"
    assert sanitize_title("-hello-") == "hello"


def test_sanitize_title_empty_returns_document():
    assert sanitize_title("") == "document"


def test_sanitize_title_whitespace_only_returns_document():
    assert sanitize_title("   ") == "document"


def test_sanitize_title_only_special_chars_returns_document():
    assert sanitize_title("///") == "document"


# ---------------------------------------------------------------------------
# ExportOptions tests
# ---------------------------------------------------------------------------

def test_export_options_defaults():
    opts = ExportOptions()
    assert opts.document_title == "document"
    assert opts.page_format == "A4"
    assert opts.landscape is False
    assert opts.scale == 1.0
    assert opts.slide_width == 13.333
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
