"""Tests for the LLM-based intent router (Haiku 4.5 classification)."""

import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure env vars are set before any app imports
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

from app.services.router import classify_request, _reset_client  # noqa: E402


@pytest.fixture(autouse=True)
def reset_router():
    """Clear the cached Anthropic client singleton between tests."""
    _reset_client()
    yield
    _reset_client()


def _mock_response(route: str) -> MagicMock:
    """Create a mock Anthropic Messages response returning the given route."""
    mock_text_block = MagicMock()
    mock_text_block.text = route

    mock_usage = MagicMock()
    mock_usage.input_tokens = 50
    mock_usage.output_tokens = 1

    mock_resp = MagicMock()
    mock_resp.content = [mock_text_block]
    mock_resp.usage = mock_usage
    return mock_resp


@contextmanager
def _mock_haiku(route: str):
    """Context manager that patches the Anthropic client and cost_tracker."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_response(route))
    mock_tracker = AsyncMock()

    with patch("app.services.router._get_client", return_value=mock_client), \
         patch("app.services.cost_tracker.cost_tracker", mock_tracker):
        yield mock_client


# ---------------------------------------------------------------------------
# Rule 1: No existing HTML → always CREATE (no LLM call)
# ---------------------------------------------------------------------------


async def test_no_html_returns_create():
    assert await classify_request("anything at all", has_existing_html=False) == "create"


async def test_no_html_even_with_edit_words():
    assert await classify_request("Change the title", has_existing_html=False) == "create"


# ---------------------------------------------------------------------------
# Edit intents (LLM returns "edit")
# ---------------------------------------------------------------------------


async def test_edit_request_with_html():
    with _mock_haiku("edit"):
        assert await classify_request("Change the title to X", has_existing_html=True) == "edit"


async def test_generic_request_defaults_to_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Make it blue", has_existing_html=True) == "edit"


async def test_improve_formatting_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Improve the formatting", has_existing_html=True) == "edit"


async def test_empty_input_with_html_defaults_to_edit():
    with _mock_haiku("edit"):
        assert await classify_request("", has_existing_html=True) == "edit"


# ---------------------------------------------------------------------------
# Diagram/chart/graph → EDIT (Claude generates content-aware SVGs)
# ---------------------------------------------------------------------------


async def test_diagram_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Add a diagram showing the process", has_existing_html=True) == "edit"


async def test_chart_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Create a bar chart of revenue", has_existing_html=True) == "edit"


async def test_flowchart_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Add a flowchart", has_existing_html=True) == "edit"


# ---------------------------------------------------------------------------
# Standalone content → CREATE (new document)
# ---------------------------------------------------------------------------


async def test_infographic_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Add an infographic about costs", has_existing_html=True) == "create"


async def test_mindmap_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Generate a mind map from the content", has_existing_html=True) == "create"


async def test_create_a_new_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Create a new impact assessment", has_existing_html=True) == "create"


async def test_start_over_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Start over", has_existing_html=True) == "create"


async def test_from_scratch_is_create():
    with _mock_haiku("create"):
        assert await classify_request("Build it from scratch", has_existing_html=True) == "create"


# ---------------------------------------------------------------------------
# Raster image requests → IMAGE (Nano Banana Pro)
# ---------------------------------------------------------------------------


async def test_photo_is_image():
    with _mock_haiku("image"):
        assert await classify_request("Add a photo of a sunset", has_existing_html=True) == "image"


async def test_picture_is_image():
    with _mock_haiku("image"):
        assert await classify_request("Add a picture of a cat", has_existing_html=True) == "image"


async def test_add_visual_is_image():
    with _mock_haiku("image"):
        assert await classify_request("Generate an image: sunset over mountains", has_existing_html=True) == "image"


# ---------------------------------------------------------------------------
# Negative intent → EDIT (not IMAGE)
# ---------------------------------------------------------------------------


async def test_remove_image_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Remove the image", has_existing_html=True) == "edit"


async def test_delete_picture_is_edit():
    with _mock_haiku("edit"):
        assert await classify_request("Delete the picture", has_existing_html=True) == "edit"


# ---------------------------------------------------------------------------
# Error handling → always fallback to EDIT
# ---------------------------------------------------------------------------


async def test_api_error_falls_back_to_edit():
    """Any API exception should return 'edit' as the safe default."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

    with patch("app.services.router._get_client", return_value=mock_client):
        assert await classify_request("Add a photo", has_existing_html=True) == "edit"


async def test_timeout_falls_back_to_edit():
    """Timeout should return 'edit' as the safe default."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=TimeoutError("Request timed out")
    )

    with patch("app.services.router._get_client", return_value=mock_client):
        assert await classify_request("Add a photo", has_existing_html=True) == "edit"


async def test_invalid_response_falls_back_to_edit():
    """If the LLM returns something other than create/edit/image, default to edit."""
    with _mock_haiku("banana"):
        assert await classify_request("Some request", has_existing_html=True) == "edit"


# ---------------------------------------------------------------------------
# Infrastructure: correct params passed, cost tracked
# ---------------------------------------------------------------------------


async def test_correct_params_passed_to_haiku():
    """Verify the correct model, max_tokens, temperature are passed to the API."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_response("edit"))

    with patch("app.services.router._get_client", return_value=mock_client):
        await classify_request("Change the title", has_existing_html=True)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 1
    assert call_kwargs["temperature"] == 0


async def test_cost_tracked_on_success():
    """Verify cost_tracker.record_usage is called after successful classification."""
    mock_cost_tracker = AsyncMock()

    with _mock_haiku("edit"), \
         patch("app.services.router.cost_tracker", mock_cost_tracker, create=True), \
         patch("app.services.cost_tracker.cost_tracker", mock_cost_tracker):
        await classify_request("Change title", has_existing_html=True)

    mock_cost_tracker.record_usage.assert_called_once_with(
        "claude-haiku-4-5-20251001", 50, 1
    )


# ---------------------------------------------------------------------------
# Pre-routing: Removal keywords → EDIT (no LLM call, Plan 015)
# ---------------------------------------------------------------------------


async def test_remove_svg_diagram_is_edit():
    """'REMOVE THE SVG DIAGRAM' must route to edit, not image."""
    result = await classify_request("REMOVE THE SVG DIAGRAM", has_existing_html=True)
    assert result == "edit"


async def test_get_rid_of_image_is_edit():
    result = await classify_request("Get rid of the image at the top", has_existing_html=True)
    assert result == "edit"


async def test_eliminate_chart_is_edit():
    result = await classify_request("Eliminate the chart section", has_existing_html=True)
    assert result == "edit"


# ---------------------------------------------------------------------------
# Pre-routing: Transform intent → CREATE (no LLM call, Plan 015)
# ---------------------------------------------------------------------------


async def test_turn_into_stakeholder_brief_is_create():
    result = await classify_request(
        "Turn the content into stakeholder brief instead", has_existing_html=True
    )
    assert result == "create"


async def test_convert_to_dashboard_is_create():
    result = await classify_request("Convert this to a dashboard", has_existing_html=True)
    assert result == "create"


async def test_rewrite_as_brd_is_create():
    result = await classify_request("Rewrite this as a BRD", has_existing_html=True)
    assert result == "create"


async def test_instead_at_end_is_create():
    """Message ending with 'instead' should route to create."""
    result = await classify_request(
        "Make it a presentation instead", has_existing_html=True
    )
    assert result == "create"


# ---------------------------------------------------------------------------
# Pre-routing: Normal requests still fall through to LLM
# ---------------------------------------------------------------------------


async def test_change_title_still_uses_llm():
    """Non-matching requests should still call Haiku."""
    with _mock_haiku("edit"):
        result = await classify_request(
            "Change the title to something better", has_existing_html=True
        )
        assert result == "edit"
