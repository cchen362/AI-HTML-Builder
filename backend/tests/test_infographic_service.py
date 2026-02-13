"""Tests for the InfographicService two-LLM pipeline."""

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.services.infographic_service import (
    ART_DIRECTOR_SYSTEM_PROMPT,
    InfographicService,
    wrap_infographic_html,
)
from app.providers.base import GenerationResult, ImageResponse


@pytest.fixture
def mock_prompt_provider():
    """Mock Gemini 2.5 Pro (art director)."""
    provider = AsyncMock()
    provider.generate.return_value = GenerationResult(
        text="A 2560x1440 landscape infographic titled 'Q4 REVENUE' with teal palette...",
        input_tokens=500,
        output_tokens=200,
        model="gemini-2.5-pro",
    )
    return provider


@pytest.fixture
def mock_image_provider():
    """Mock Nano Banana Pro (renderer)."""
    provider = AsyncMock()
    provider.generate_image.return_value = ImageResponse(
        image_bytes=b"\x89PNG" + b"\x00" * 100,
        format="PNG",
        width=2560,
        height=1440,
        model="gemini-3-pro-image-preview",
        prompt="test prompt",
    )
    return provider


@pytest.fixture
def service(mock_prompt_provider, mock_image_provider):
    return InfographicService(mock_prompt_provider, mock_image_provider)


# --- Two-LLM pipeline ---


async def test_generate_calls_both_providers(
    service, mock_prompt_provider, mock_image_provider
):
    """Pipeline should call art director (prompt) then renderer (image)."""
    result = await service.generate("Create an infographic about Q4 revenue")
    mock_prompt_provider.generate.assert_called_once()
    mock_image_provider.generate_image.assert_called_once()
    assert result.image_bytes == b"\x89PNG" + b"\x00" * 100
    assert result.image_format == "PNG"
    assert result.model_prompt == "gemini-2.5-pro"
    assert result.model_image == "gemini-3-pro-image-preview"


async def test_generate_passes_visual_prompt_to_image_provider(
    service, mock_prompt_provider, mock_image_provider
):
    """The art director's output should be sent to the image provider."""
    await service.generate("Revenue infographic")
    img_call_args = mock_image_provider.generate_image.call_args
    prompt_sent = img_call_args[0][0]  # First positional arg
    assert "Q4 REVENUE" in prompt_sent  # From mock_prompt_provider fixture


async def test_generate_returns_visual_prompt(service):
    """The visual prompt should be available in the result for storage."""
    result = await service.generate("Test")
    assert "Q4 REVENUE" in result.visual_prompt
    assert result.prompt_input_tokens == 500
    assert result.prompt_output_tokens == 200


# --- Content context ---


async def test_generate_with_content_context(service, mock_prompt_provider):
    """Content context (existing doc) should appear in art director messages."""
    await service.generate(
        "Turn this into an infographic",
        content_context="<h1>Revenue Report</h1><p>$5M total</p>",
    )
    call_kwargs = mock_prompt_provider.generate.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]
    # Source material should be in first user message
    assert any("source content" in m["content"].lower() for m in messages if m["role"] == "user")
    assert any("Revenue Report" in m["content"] for m in messages if m["role"] == "user")


# --- Iteration with previous visual prompt ---


async def test_generate_with_previous_visual_prompt(service, mock_prompt_provider):
    """Iteration should pass the previous visual prompt to the art director."""
    prev_prompt = "A teal infographic showing revenue growth..."
    await service.generate(
        "Change the theme to navy",
        previous_visual_prompt=prev_prompt,
    )
    call_kwargs = mock_prompt_provider.generate.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1]["messages"]
    # Previous prompt should appear in messages
    assert any("teal infographic" in m["content"] for m in messages if m["role"] == "user")
    # User's modification request should be the last message
    assert messages[-1]["content"] == "Change the theme to navy"


# --- Fallback ---


async def test_generate_uses_fallback_on_primary_failure(mock_prompt_provider):
    """When primary image provider fails, fallback should be used."""
    primary = AsyncMock()
    primary.generate_image.side_effect = RuntimeError("Primary failed")

    fallback = AsyncMock()
    fallback.generate_image.return_value = ImageResponse(
        image_bytes=b"\x89PNG\x00",
        format="PNG",
        width=2560,
        height=1440,
        model="gemini-2.5-flash-image",
        prompt="test",
    )

    svc = InfographicService(mock_prompt_provider, primary, fallback)
    result = await svc.generate("Test infographic")
    assert result.model_image == "gemini-2.5-flash-image"


async def test_generate_raises_when_all_fail(mock_prompt_provider):
    """When all image providers fail, should raise RuntimeError."""
    primary = AsyncMock()
    primary.generate_image.side_effect = RuntimeError("Primary failed")

    fallback = AsyncMock()
    fallback.generate_image.side_effect = RuntimeError("Fallback failed")

    svc = InfographicService(mock_prompt_provider, primary, fallback)
    with pytest.raises(RuntimeError, match="failed after all attempts"):
        await svc.generate("Test infographic")


# --- HTML wrapper ---


def test_wrap_infographic_html_structure():
    """Wrapper should produce valid minimal HTML with base64 image."""
    html = wrap_infographic_html(b"\x89PNG\x00\x00", "PNG", "Test infographic")
    assert "<!DOCTYPE html>" in html
    assert "data:image/png;base64," in html
    assert 'alt="Test infographic"' in html
    # Must NOT have semantic sections (used by _is_infographic_doc detection)
    assert "<main" not in html
    assert "<header" not in html
    assert "<section" not in html


def test_wrap_infographic_html_dark_background():
    """Wrapper should use dark background matching app theme."""
    html = wrap_infographic_html(b"\x89PNG", "PNG", "Test")
    assert "#0a0a0f" in html


def test_wrap_infographic_html_escapes_alt():
    """Alt text should be properly escaped."""
    html = wrap_infographic_html(b"\x89PNG", "PNG", 'Test "quoted" & <special>')
    assert "&quot;" in html
    assert "&lt;" in html


def test_wrap_infographic_html_truncates_alt():
    """Alt text should be truncated to 200 chars."""
    long_alt = "x" * 300
    html = wrap_infographic_html(b"\x89PNG", "PNG", long_alt)
    # The alt attribute value should be <= 200 chars
    import re
    match = re.search(r'alt="([^"]*)"', html)
    assert match
    assert len(match.group(1)) <= 200


# --- Art director prompt ---


def test_art_director_system_prompt_specifies_canvas():
    assert "2560" in ART_DIRECTOR_SYSTEM_PROMPT
    assert "1440" in ART_DIRECTOR_SYSTEM_PROMPT


def test_art_director_system_prompt_mentions_text_accuracy():
    assert "literally" in ART_DIRECTOR_SYSTEM_PROMPT.lower()
