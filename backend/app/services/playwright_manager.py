"""Playwright browser lifecycle manager for PDF/PNG exports."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog
from playwright.async_api import Browser, Page, Playwright, async_playwright

logger = structlog.get_logger()


class PlaywrightManager:
    """Manages Playwright browser lifecycle with crash recovery."""

    def __init__(self) -> None:
        self._browser: Browser | None = None
        self._playwright: Playwright | None = None
        self._health_check_task: asyncio.Task[None] | None = None
        self._last_health_check: datetime | None = None
        self._restart_lock: asyncio.Lock | None = None

    async def initialize(self) -> None:
        """Initialize Playwright and launch browser. Called during app startup."""
        try:
            logger.info("Initializing Playwright browser")
            self._restart_lock = asyncio.Lock()
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(  # type: ignore[union-attr]
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            logger.info("Playwright browser launched", version=self._browser.version)
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        except Exception as e:
            logger.error("Failed to initialize Playwright", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Shutdown browser and Playwright. Called during app shutdown."""
        try:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None

            if self._browser:
                logger.info("Closing Playwright browser")
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()  # type: ignore[union-attr]
                self._playwright = None

            logger.info("Playwright shutdown complete")
        except Exception as e:
            logger.error("Error during Playwright shutdown", error=str(e))

    async def create_page(self) -> Page:
        """Create a new browser page with automatic recovery."""
        if not self._browser:
            if not self._restart_lock:
                self._restart_lock = asyncio.Lock()
            async with self._restart_lock:
                if not self._browser:
                    logger.warning("Browser not initialized, restarting")
                    await self._restart_browser()

        try:
            assert self._browser is not None
            return await self._browser.new_page()
        except Exception as e:
            logger.error("Failed to create page", error=str(e))
            if not self._restart_lock:
                self._restart_lock = asyncio.Lock()
            async with self._restart_lock:
                logger.info("Attempting browser restart after page failure")
                await self._restart_browser()
                assert self._browser is not None
                return await self._browser.new_page()

    async def _restart_browser(self) -> None:
        """Restart browser after crash or failure."""
        try:
            logger.warning("Restarting Playwright browser")
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None

            assert self._playwright is not None
            self._browser = await self._playwright.chromium.launch(  # type: ignore[union-attr]
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            logger.info("Browser restarted", version=self._browser.version)
        except Exception as e:
            logger.error("Failed to restart browser", error=str(e))
            raise

    async def _health_check_loop(self) -> None:
        """Periodic health check to detect browser crashes."""
        while True:
            try:
                await asyncio.sleep(30)
                if self._browser:
                    try:
                        test_page = await self._browser.new_page()
                        await test_page.close()
                        self._last_health_check = datetime.now()
                        logger.debug("Browser health check passed")
                    except Exception as e:
                        logger.error("Browser health check failed", error=str(e))
                        if self._restart_lock:
                            async with self._restart_lock:
                                await self._restart_browser()
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))

    @property
    def is_initialized(self) -> bool:
        return self._browser is not None

    @property
    def last_health_check(self) -> datetime | None:
        return self._last_health_check


playwright_manager = PlaywrightManager()
