"""Tests for Playwright browser lifecycle manager."""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing")

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.playwright_manager import PlaywrightManager


@pytest.fixture
def manager():
    """Fresh PlaywrightManager for each test (not the module singleton)."""
    return PlaywrightManager()


@pytest.mark.asyncio
async def test_initialize_launches_browser(manager: PlaywrightManager):
    mock_browser = MagicMock()
    mock_browser.version = "120.0"
    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    with patch(
        "app.services.playwright_manager.async_playwright"
    ) as mock_async_pw:
        mock_context = AsyncMock()
        mock_context.start = AsyncMock(return_value=mock_pw)
        mock_async_pw.return_value = mock_context

        await manager.initialize()

    assert manager.is_initialized
    mock_pw.chromium.launch.assert_awaited_once()

    # Cleanup: cancel health check task
    if manager._health_check_task:
        manager._health_check_task.cancel()
        try:
            await manager._health_check_task
        except (asyncio.CancelledError, Exception):
            pass


@pytest.mark.asyncio
async def test_shutdown_closes_browser(manager: PlaywrightManager):
    mock_browser = AsyncMock()
    mock_pw = AsyncMock()
    manager._browser = mock_browser
    manager._playwright = mock_pw

    await manager.shutdown()

    mock_browser.close.assert_awaited_once()
    mock_pw.stop.assert_awaited_once()
    assert not manager.is_initialized


@pytest.mark.asyncio
async def test_shutdown_idempotent(manager: PlaywrightManager):
    """Calling shutdown when not initialized should not error."""
    await manager.shutdown()
    assert not manager.is_initialized


@pytest.mark.asyncio
async def test_is_initialized_false_by_default(manager: PlaywrightManager):
    assert not manager.is_initialized


@pytest.mark.asyncio
async def test_last_health_check_none_by_default(manager: PlaywrightManager):
    assert manager.last_health_check is None


@pytest.mark.asyncio
async def test_create_page_returns_page(manager: PlaywrightManager):
    mock_page = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    manager._browser = mock_browser

    page = await manager.create_page()
    assert page is mock_page
    mock_browser.new_page.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_page_restarts_on_none_browser(manager: PlaywrightManager):
    """When browser is None, create_page should attempt restart."""
    mock_page = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    manager._playwright = mock_pw
    manager._browser = None

    page = await manager.create_page()

    assert page is mock_page
    mock_pw.chromium.launch.assert_awaited_once()
