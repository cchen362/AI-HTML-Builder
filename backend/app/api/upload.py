"""File upload API endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


@router.post("/api/upload")
async def upload_file(file: UploadFile) -> dict:
    """
    Upload and process a file for context injection into chat.

    Accepts: .txt, .md, .docx, .pdf, .csv, .xlsx (max configurable, default 50MB)
    Returns: Extracted content, metadata, and suggested prompt.
    """
    from app.utils.file_processors import (
        FileProcessingError,
        generate_upload_prompt,
        process_file,
        validate_file,
    )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()

    try:
        validate_file(file.filename, len(content), settings.max_upload_size_mb)
    except FileProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await process_file(file.filename, content)
        suggested_prompt = generate_upload_prompt(result)

        logger.info(
            "File uploaded and processed",
            filename=file.filename,
            content_type=result["content_type"],
            size_bytes=len(content),
        )

        return {
            "success": True,
            "data": result,
            "suggested_prompt": suggested_prompt,
        }

    except FileProcessingError as e:
        logger.warning("File processing failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected file processing error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process file: {e}"
        )
