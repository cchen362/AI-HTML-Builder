import asyncio
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import pytest
from unittest.mock import AsyncMock, patch
from app.services.image_service import (
    ImageService,
    _insert_into_html,
    _compress_image,
    _flowchart_svg,
    _chart_svg,
    _timeline_svg,
    _placeholder_svg,
)
from app.providers.base import ImageProvider, ImageResponse


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body>
<header><h1>Title</h1></header>
<main>
<section><p>Content here.</p></section>
</main>
</body>
</html>"""


SAMPLE_HTML_NO_MAIN = """<!DOCTYPE html>
<html><body><p>Simple page</p></body></html>"""


@pytest.fixture
def mock_provider():
    return AsyncMock(spec=ImageProvider)


@pytest.fixture
def service(mock_provider):
    return ImageService(mock_provider)


# --- should_use_svg tests ---


def test_should_use_svg_flowchart(service):
    use_svg, svg_type = service.should_use_svg("Add a flowchart showing the process")
    assert use_svg is True
    assert svg_type == "flowchart"


def test_should_use_svg_chart(service):
    use_svg, svg_type = service.should_use_svg("Create a bar chart of revenue")
    assert use_svg is True
    assert svg_type == "chart"


def test_should_use_svg_timeline(service):
    use_svg, svg_type = service.should_use_svg("Show a timeline of milestones")
    assert use_svg is True
    assert svg_type == "timeline"


def test_should_use_svg_diagram(service):
    use_svg, svg_type = service.should_use_svg("Add a diagram of the architecture")
    assert use_svg is True
    assert svg_type == "flowchart"  # "diagram" maps to flowchart


def test_should_use_svg_false_for_photo(service):
    use_svg, svg_type = service.should_use_svg("Add a photo of mountains")
    assert use_svg is False
    assert svg_type == ""


def test_should_use_svg_false_for_generic(service):
    use_svg, svg_type = service.should_use_svg("Change the header color")
    assert use_svg is False
    assert svg_type == ""


# --- _insert_into_html tests ---


def test_insert_before_main():
    result = _insert_into_html(SAMPLE_HTML, "<p>New content</p>")
    assert "<p>New content</p>\n</main>" in result
    assert result.count("<p>New content</p>") == 1


def test_insert_before_body_when_no_main():
    result = _insert_into_html(SAMPLE_HTML_NO_MAIN, "<p>New</p>")
    assert "<p>New</p>\n</body>" in result


def test_insert_fallback_appends():
    html = "<div>No body tag</div>"
    result = _insert_into_html(html, "<p>Appended</p>")
    assert result == "<div>No body tag</div><p>Appended</p>"


# --- generate_svg_and_embed tests ---


def test_generate_svg_and_embed_flowchart(service):
    result = service.generate_svg_and_embed(SAMPLE_HTML, "flowchart", "test process")
    assert '<div class="generated-svg"' in result
    assert "<svg" in result
    assert "#0D7377" in result  # Project color palette
    assert "Start" in result
    assert "Process" in result
    assert "End" in result


def test_generate_svg_and_embed_chart(service):
    result = service.generate_svg_and_embed(SAMPLE_HTML, "chart", "revenue data")
    assert "<svg" in result
    assert "Q1" in result
    assert "Q2" in result


def test_generate_svg_and_embed_timeline(service):
    result = service.generate_svg_and_embed(SAMPLE_HTML, "timeline", "project milestones")
    assert "<svg" in result
    assert "Phase 1" in result
    assert "Complete" in result


def test_generate_svg_and_embed_placeholder(service):
    result = service.generate_svg_and_embed(SAMPLE_HTML, "unknown", "some diagram")
    assert "<svg" in result
    assert "some diagram" in result


# --- generate_and_embed tests ---


@pytest.mark.asyncio
async def test_generate_and_embed_calls_provider(mock_provider, service):
    mock_provider.generate_image.return_value = ImageResponse(
        image_bytes=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
        format="PNG",
        width=1920,
        height=1080,
        model="gemini-image",
        prompt="test image",
    )

    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        updated_html, img_resp = await service.generate_and_embed(
            SAMPLE_HTML, "A beautiful sunset", resolution="hd"
        )

    mock_provider.generate_image.assert_called_once_with("A beautiful sunset", "hd")
    assert "data:image/png;base64," in updated_html
    assert img_resp.model == "gemini-image"


@pytest.mark.asyncio
async def test_generate_and_embed_no_provider():
    service = ImageService(image_provider=None)
    with pytest.raises(RuntimeError, match="No image provider configured"):
        await service.generate_and_embed(SAMPLE_HTML, "test")


# --- SVG templates use project palette ---


def test_flowchart_svg_uses_project_colors():
    svg = _flowchart_svg()
    assert "#0D7377" in svg  # Deep Teal
    assert "#14B8A6" in svg  # Teal
    assert "#059669" in svg  # Emerald


def test_chart_svg_uses_project_colors():
    svg = _chart_svg()
    assert "#0D7377" in svg
    assert "#14B8A6" in svg


def test_timeline_svg_uses_project_colors():
    svg = _timeline_svg()
    assert "#0D7377" in svg
    assert "#059669" in svg


def test_placeholder_svg_escapes_html():
    svg = _placeholder_svg('Test "with" <special> & chars')
    assert "&quot;" in svg or '"' not in svg.split("</text>")[0]
    assert "&lt;" in svg
    assert "&amp;" in svg


# --- _compress_image tests ---


def test_compress_image_already_small():
    """Small images should be returned as-is via quality reduction."""
    from io import BytesIO
    from PIL import Image

    # Create a small JPEG
    img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    small_bytes = buf.getvalue()

    result = _compress_image(small_bytes, "JPEG")
    assert len(result) > 0
    assert len(result) <= 5 * 1024 * 1024


# --- Retry / Fallback Tests ---


async def test_retry_succeeds_on_second_attempt():
    """Primary fails once, succeeds on retry."""
    mock_provider = AsyncMock(spec=ImageProvider)
    mock_provider.generate_image.side_effect = [
        RuntimeError("503 overloaded"),
        ImageResponse(
            image_bytes=b"fake-png-data",
            format="PNG",
            width=1920,
            height=1080,
            model="gemini-3-pro-image-preview",
            prompt="test",
        ),
    ]
    service = ImageService(mock_provider)
    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-3-pro-image-preview"
    assert mock_provider.generate_image.call_count == 2


async def test_fallback_to_flash_on_double_failure():
    """Primary fails twice, fallback succeeds."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"fallback-data",
        format="PNG",
        width=1920,
        height=1080,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-2.5-flash-image"
    assert mock_primary.generate_image.call_count == 2
    assert mock_fallback.generate_image.call_count == 1


async def test_timeout_triggers_retry():
    """Primary hangs (timeout), fallback succeeds."""
    async def hang_forever(*args, **kwargs):
        await asyncio.sleep(999)

    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = hang_forever

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"fallback-data",
        format="PNG",
        width=1920,
        height=1080,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 1  # Short timeout for test speed
        result = await service._generate_with_retry("test prompt", "hd")
    assert result.model == "gemini-2.5-flash-image"


async def test_all_attempts_fail_raises():
    """All attempts fail, exception propagates."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    mock_fallback = AsyncMock(spec=ImageProvider)
    mock_fallback.generate_image.side_effect = RuntimeError("Flash also failed")

    service = ImageService(mock_primary, fallback_provider=mock_fallback)
    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        with pytest.raises(RuntimeError, match="Image generation failed"):
            await service._generate_with_retry("test prompt", "hd")


async def test_no_fallback_provider_raises_after_retries():
    """No fallback configured, raises after primary retries exhausted."""
    mock_primary = AsyncMock(spec=ImageProvider)
    mock_primary.generate_image.side_effect = RuntimeError("503")

    service = ImageService(mock_primary)  # No fallback
    with patch("app.config.settings") as mock_settings:
        mock_settings.image_timeout_seconds = 90
        with pytest.raises(RuntimeError, match="no fallback"):
            await service._generate_with_retry("test prompt", "hd")
    assert mock_primary.generate_image.call_count == 2
