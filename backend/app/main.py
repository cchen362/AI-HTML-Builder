import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import structlog

from app.config import settings
from app.database import init_db, close_db

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
    logger.info("Application started")
    yield
    # Shutdown
    await close_db()
    logger.info("Application stopped")


app = FastAPI(title="AI HTML Builder", lifespan=lifespan)

# Import and register API routers
from app.api import chat, sessions, health, costs  # noqa: E402

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(health.router)
app.include_router(costs.router)

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
