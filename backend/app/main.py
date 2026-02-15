import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import structlog

from app.config import settings
from app.database import init_db, close_db, get_db
from app.auth_database import init_auth_db, close_auth_db

# Configure structlog with proper log level mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        LOG_LEVELS.get(settings.log_level.lower(), logging.INFO)
    ),
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await init_auth_db()

    # Register exporters
    from app.services.export_service import register_exporter, _export_html, list_available_formats

    register_exporter("html", "HTML", _export_html)

    # PPTX exporter (requires Anthropic API key)
    try:
        from app.providers.anthropic_provider import AnthropicProvider
        from app.services.exporters.pptx_exporter import PPTXExporter

        pptx_provider = AnthropicProvider()
        pptx_exporter = PPTXExporter(pptx_provider)
        register_exporter("pptx", "PowerPoint", pptx_exporter.export)
    except (ValueError, Exception) as exc:
        logger.warning("PPTX export unavailable", reason=str(exc))

    # PDF + PNG exporters (require Playwright)
    try:
        from app.services.playwright_manager import playwright_manager
        from app.services.exporters.playwright_exporter import export_pdf, export_png

        await playwright_manager.initialize()
        register_exporter("pdf", "PDF", export_pdf)
        register_exporter("png", "PNG", export_png)
    except Exception as exc:
        logger.warning("PDF/PNG export unavailable", reason=str(exc))

    # Background cleanup: delete sessions inactive for 7+ days (runs every 6 hours)
    async def _cleanup_loop() -> None:
        while True:
            try:
                await asyncio.sleep(6 * 3600)
                db = await get_db()
                cursor = await db.execute(
                    "DELETE FROM sessions WHERE last_active < datetime('now', '-7 days')"
                )
                await db.commit()
                if cursor.rowcount:
                    logger.info("Cleaned old sessions", count=cursor.rowcount)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error", error=str(e))

    cleanup_task = asyncio.create_task(_cleanup_loop())

    logger.info("Application started", export_formats=list(list_available_formats()))
    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        from app.services.playwright_manager import playwright_manager as pw_mgr

        await pw_mgr.shutdown()
    except Exception:
        pass
    await close_auth_db()
    await close_db()
    logger.info("Application stopped")


app = FastAPI(title="AI HTML Builder", lifespan=lifespan)

# Import and register API routers
from app.api import auth, chat, sessions, health, costs, export, upload  # noqa: E402

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(health.router)
app.include_router(costs.router)
app.include_router(export.router)
app.include_router(upload.router)

# Serve static frontend files (built React app)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve the React SPA for all non-API routes."""
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))
