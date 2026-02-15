"""Tests for PDF and PNG exporters (both use Playwright mocks)."""

import base64
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.exporters.base import ExportError, ExportGenerationError, ExportOptions
from app.services.exporters.playwright_exporter import (
    _inject_print_css,
    export_infographic_png,
    export_pdf,
    export_png,
)

SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Test</h1></body></html>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_page(pdf_bytes: bytes = b"%PDF-fake", png_bytes: bytes = b"\x89PNG-fake"):
    """Create a mock Playwright page."""
    page = AsyncMock()
    page.set_viewport_size = AsyncMock()
    page.set_content = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.pdf = AsyncMock(return_value=pdf_bytes)
    page.screenshot = AsyncMock(return_value=png_bytes)
    page.close = AsyncMock()
    return page


# ---------------------------------------------------------------------------
# PDF Exporter tests
# ---------------------------------------------------------------------------

class TestPDFExporter:
    def test_properties(self):
        # Verify export_pdf returns correct content_type and extension
        pass  # Tested via test_pdf_export_basic

    @pytest.mark.asyncio
    async def test_pdf_export_basic(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(document_title="test")
            result = await export_pdf(SAMPLE_HTML, options)

        assert result.content == b"%PDF-fake"
        assert result.content_type == "application/pdf"
        assert result.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_pdf_export_passes_options(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(
                document_title="test",
                page_format="Letter",
                landscape=True,
                scale=0.9,
            )
            await export_pdf(SAMPLE_HTML, options)

        call_kwargs = mock_page.pdf.call_args[1]
        assert call_kwargs["format"] == "Letter"
        assert call_kwargs["landscape"] is True
        assert call_kwargs["scale"] == 0.9
        assert call_kwargs["print_background"] is True

    @pytest.mark.asyncio
    async def test_pdf_export_closes_page_on_success(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            await export_pdf(SAMPLE_HTML, ExportOptions())

        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pdf_export_closes_page_on_error(self):
        mock_page = _make_mock_page()
        mock_page.pdf = AsyncMock(side_effect=RuntimeError("pdf failed"))
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            with pytest.raises(ExportGenerationError, match="PDF generation failed"):
                await export_pdf(SAMPLE_HTML, ExportOptions())

        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pdf_export_metadata(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            result = await export_pdf(SAMPLE_HTML, ExportOptions(page_format="A4"))

        assert result.metadata is not None
        assert result.metadata["page_format"] == "A4"
        assert result.metadata["rendered_with"] == "playwright-chromium"


# ---------------------------------------------------------------------------
# PNG Exporter tests
# ---------------------------------------------------------------------------

class TestPNGExporter:
    @pytest.mark.asyncio
    async def test_png_export_basic(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(document_title="shot")
            result = await export_png(SAMPLE_HTML, options)

        assert result.content == b"\x89PNG-fake"
        assert result.content_type == "image/png"
        assert result.filename == "shot.png"

    @pytest.mark.asyncio
    async def test_png_export_full_page(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(full_page=True)
            await export_png(SAMPLE_HTML, options)

        call_kwargs = mock_page.screenshot.call_args[1]
        assert call_kwargs["full_page"] is True

    @pytest.mark.asyncio
    async def test_png_export_custom_viewport(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(width=800, height=600, full_page=False)
            await export_png(SAMPLE_HTML, options)

        mock_page.set_viewport_size.assert_awaited_with(
            {"width": 800, "height": 600}
        )

    @pytest.mark.asyncio
    async def test_png_export_closes_page_on_success(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            await export_png(SAMPLE_HTML, ExportOptions())

        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_png_export_closes_page_on_error(self):
        mock_page = _make_mock_page()
        mock_page.screenshot = AsyncMock(side_effect=RuntimeError("screenshot failed"))
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            with pytest.raises(ExportGenerationError, match="PNG generation failed"):
                await export_png(SAMPLE_HTML, ExportOptions())

        mock_page.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_png_export_metadata_with_dimensions(self):
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            options = ExportOptions(width=1024, height=768)
            result = await export_png(SAMPLE_HTML, options)

        assert result.metadata is not None
        assert result.metadata["width"] == 1024
        assert result.metadata["height"] == 768


# ---------------------------------------------------------------------------
# Print CSS injection tests
# ---------------------------------------------------------------------------

class TestPrintCSSInjection:
    def test_inject_print_css_inserts_before_head(self):
        html = '<!DOCTYPE html><html><head><title>Test</title></head><body></body></html>'
        result = _inject_print_css(html)
        assert '@media print' in result
        assert result.index('@media print') < result.index('</head>')

    def test_inject_print_css_no_head_tag(self):
        html = '<html><body>no head</body></html>'
        result = _inject_print_css(html)
        assert result == html  # unchanged

    def test_inject_print_css_includes_break_rules(self):
        html = '<html><head></head><body></body></html>'
        result = _inject_print_css(html)
        assert 'break-inside: avoid' in result
        assert 'break-after: avoid' in result
        assert 'orphans: 3' in result

    def test_inject_print_css_only_replaces_first_head(self):
        html = '<html><head></head><body></body></html><!-- </head> -->'
        result = _inject_print_css(html)
        assert result.count('@media print') == 1

    @pytest.mark.asyncio
    async def test_pdf_export_includes_print_css(self):
        """Verify that export_pdf injects print CSS before rendering."""
        html_with_head = '<!DOCTYPE html><html><head><title>T</title></head><body><h1>Test</h1></body></html>'
        mock_page = _make_mock_page()
        with patch("app.services.exporters.playwright_exporter.playwright_manager") as mock_mgr:
            mock_mgr.create_page = AsyncMock(return_value=mock_page)
            await export_pdf(html_with_head, ExportOptions())

        # The HTML passed to set_content should include our print CSS
        set_content_call = mock_page.set_content.call_args
        rendered_html = set_content_call[0][0]
        assert '@media print' in rendered_html


# ---------------------------------------------------------------------------
# Infographic PNG export tests
# ---------------------------------------------------------------------------

class TestInfographicPNGExport:
    @pytest.mark.asyncio
    async def test_export_infographic_png_extracts_bytes(self):
        test_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        b64 = base64.b64encode(test_bytes).decode()
        html = f'<html><body><img src="data:image/png;base64,{b64}" alt="test"/></body></html>'
        result = await export_infographic_png(html, ExportOptions())
        assert result.content == test_bytes
        assert result.content_type == 'image/png'
        assert result.file_extension == 'png'

    @pytest.mark.asyncio
    async def test_export_infographic_png_jpeg_format(self):
        test_bytes = b'\xff\xd8\xff' + b'\x00' * 100
        b64 = base64.b64encode(test_bytes).decode()
        html = f'<html><body><img src="data:image/jpeg;base64,{b64}" /></body></html>'
        result = await export_infographic_png(html, ExportOptions())
        assert result.content == test_bytes
        assert result.content_type == 'image/jpeg'
        assert result.file_extension == 'jpg'

    @pytest.mark.asyncio
    async def test_export_infographic_png_no_image(self):
        html = '<html><body>No image here</body></html>'
        with pytest.raises(ExportError, match="No embedded image"):
            await export_infographic_png(html, ExportOptions())

    @pytest.mark.asyncio
    async def test_export_infographic_png_metadata(self):
        test_bytes = b'\x89PNG' + b'\x00' * 50
        b64 = base64.b64encode(test_bytes).decode()
        html = f'<html><body><img src="data:image/png;base64,{b64}" /></body></html>'
        result = await export_infographic_png(html, ExportOptions(document_title="info"))
        assert result.metadata is not None
        assert result.metadata["source"] == "direct-base64-extraction"
        assert result.metadata["size_bytes"] == len(test_bytes)
        assert result.filename == "info.png"
