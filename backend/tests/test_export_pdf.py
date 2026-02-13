"""Tests for PDF and PNG exporters (both use Playwright mocks)."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.exporters.base import ExportGenerationError, ExportOptions
from app.services.exporters.playwright_exporter import export_pdf, export_png

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
