from datetime import datetime

from fastapi import APIRouter

from app.database import get_db

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    status: dict = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {},
    }

    # Database check
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        status["components"]["database"] = "connected"
    except Exception as e:
        status["components"]["database"] = str(e)
        status["status"] = "degraded"

    # Playwright check (lazy import — won't fail if not installed)
    try:
        from app.services.playwright_manager import playwright_manager

        if playwright_manager.is_initialized:
            status["components"]["playwright"] = "healthy"
            if playwright_manager.last_health_check:
                status["playwright_last_check"] = (
                    playwright_manager.last_health_check.isoformat()
                )
        else:
            status["components"]["playwright"] = "not_initialized"
    except ImportError:
        status["components"]["playwright"] = "not_available"

    return status
