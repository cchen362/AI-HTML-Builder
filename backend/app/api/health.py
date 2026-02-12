from fastapi import APIRouter
from app.database import get_db

router = APIRouter()


@router.get("/api/health")
async def health():
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
