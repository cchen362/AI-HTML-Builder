from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import structlog
from ...services.file_processor import FileProcessor
from ...services.redis_service import redis_service
from ...models.schemas import UploadResponse, FileInfo

logger = structlog.get_logger()
router = APIRouter()

@router.post("/upload", response_model=UploadResponse, deprecated=True)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    DEPRECATED: File upload functionality has been removed in the redesign.
    This endpoint is disabled and will return an error.
    """
    logger.warning("Upload endpoint called but is deprecated", session_id=session_id, filename=file.filename)
    raise HTTPException(
        status_code=410, 
        detail="File upload functionality has been removed. Please paste your content directly into the chat input."
    )