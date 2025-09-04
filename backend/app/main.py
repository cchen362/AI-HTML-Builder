from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from dotenv import load_dotenv

# Import services and utilities
from .services.redis_service import redis_service
from .utils.logger import configure_logging
from .core.config import settings

# Import API endpoints
from .api.endpoints.health import router as health_router
from .api.endpoints.upload import router as upload_router
from .api.endpoints.export import router as export_router
from .api.websocket import websocket_endpoint

# Load environment variables
load_dotenv()

# Configure logging
configure_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI HTML Builder API")
    
    # Initialize Redis connection
    await redis_service.connect()
    logger.info("Redis connected")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI HTML Builder API")
    await redis_service.disconnect()

app = FastAPI(
    title="AI HTML Builder",
    description="Generate styled HTML documents through AI chat interactions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(export_router, prefix="/api", tags=["export"])

# WebSocket endpoint
@app.websocket("/ws/{session_id}")
async def websocket_handler(websocket: WebSocket, session_id: str):
    await websocket_endpoint(websocket, session_id)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "AI HTML Builder API",
        "status": "ready",
        "version": "1.0.0",
        "docs": "/docs"
    }