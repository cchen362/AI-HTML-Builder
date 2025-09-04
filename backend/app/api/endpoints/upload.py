from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import structlog
from ...services.file_processor import FileProcessor
from ...services.redis_service import redis_service
from ...models.schemas import UploadResponse, FileInfo

logger = structlog.get_logger()
router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Upload and process file for text extraction
    """
    try:
        # Validate session exists
        session = await redis_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process file
        extracted_text = await FileProcessor.process_file(file)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text content found in file")
        
        # Get file info
        file_info = FileProcessor.get_file_info(file)
        
        # Log successful upload
        logger.info(
            "File uploaded and processed",
            session_id=session_id,
            filename=file.filename,
            content_length=len(extracted_text)
        )
        
        return UploadResponse(
            extracted_text=extracted_text,
            file_info=FileInfo(**file_info)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", session_id=session_id, filename=getattr(file, 'filename', 'unknown'), error=str(e))
        raise HTTPException(status_code=500, detail="Upload processing failed")