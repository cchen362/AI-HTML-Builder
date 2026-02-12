from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI Providers
    anthropic_api_key: str
    google_api_key: str = ""

    # Database
    database_path: str = "./data/app.db"

    # Server
    log_level: str = "info"
    rate_limit_requests: int = 30
    rate_limit_window: int = 60  # seconds
    session_timeout_hours: int = 24
    max_upload_size_mb: int = 50

    # Models (configurable without code change)
    edit_model: str = "claude-sonnet-4-5-20250929"
    creation_model: str = "gemini-2.5-pro"
    image_model: str = "gemini-2.0-flash-preview-image-generation"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
