from fastapi import APIRouter
import time
from ...services.redis_service import redis_service
from ...models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if await redis_service.is_healthy() else "disconnected"
    
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time()),
        redis=redis_status,
        version="1.0.0"
    )