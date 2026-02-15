"""Export API endpoints for document format conversion."""

from __future__ import annotations

import io

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.export_service import export_document, list_available_formats
from app.services.exporters.base import ExportError, ExportOptions

logger = structlog.get_logger()

router = APIRouter()


@router.post("/api/sessions/{session_id}/documents/{document_id}/export/{format_key}")
async def export(
    session_id: str,
    document_id: str,
    format_key: str,
    version: int | None = Query(None, description="Document version (None = latest)"),
    title: str = Query("document", description="Document title for filename"),
    # PPTX-specific
    slide_width: float = Query(13.333, description="Slide width in inches (13.333 for 16:9)"),
    slide_height: float = Query(7.5, description="Slide height in inches"),
    theme: str = Query("default", description="Presentation theme"),
    # PDF-specific
    page_format: str = Query("A4", description="Page format (A4, Letter, Legal)"),
    landscape: bool = Query(False, description="Landscape orientation"),
    scale: float = Query(1.0, description="Page scale (0.1 - 2.0)"),
    # PNG-specific
    full_page: bool = Query(True, description="Capture full page"),
    width: int | None = Query(None, description="Screenshot width in pixels"),
    height: int | None = Query(None, description="Screenshot height in pixels"),
) -> StreamingResponse:
    """Export a document in the requested format."""
    from app.services.session_service import session_service

    owns = await session_service.verify_document_ownership(document_id, session_id)
    if not owns:
        raise HTTPException(
            status_code=403, detail="Document does not belong to this session"
        )

    try:
        options = ExportOptions(
            document_title=title,
            slide_width=slide_width,
            slide_height=slide_height,
            theme=theme,
            page_format=page_format,
            landscape=landscape,
            scale=scale,
            full_page=full_page,
            width=width,
            height=height,
        )
        result = await export_document(
            document_id=document_id,
            format_key=format_key,
            version=version,
            options=options,
        )
        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.content_type,
            headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
        )
    except ExportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Export failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed")


@router.get("/api/export/formats")
async def get_formats() -> dict:
    """List available export formats."""
    return {"formats": list_available_formats()}
