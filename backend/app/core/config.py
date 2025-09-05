import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "info")
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Additional fields from .env
    debug: str = os.getenv("DEBUG", "false")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()