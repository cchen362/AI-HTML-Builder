from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI Providers
    anthropic_api_key: str
    google_api_key: str = ""

    # Database
    database_path: str = "./data/app.db"

    # Server
    log_level: str = "info"
    max_upload_size_mb: int = 50

    # Models (configurable without code change)
    edit_model: str = "claude-sonnet-4-5-20250929"
    creation_model: str = "gemini-2.5-pro"
    image_model: str = "gemini-3-pro-image-preview"
    image_fallback_model: str = "gemini-2.5-flash-image"
    image_timeout_seconds: int = 90

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env
