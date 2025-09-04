from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import structlog
from ...services.redis_service import redis_service
from ...models.schemas import ExportRequest

logger = structlog.get_logger()
router = APIRouter()

@router.post("/export")
async def export_html(request: ExportRequest):
    """
    Export generated HTML as downloadable file
    """
    try:
        # Validate session exists
        session = await redis_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Use provided HTML content or get from session
        html_content = request.html_content or session.current_html
        
        if not html_content:
            raise HTTPException(status_code=400, detail="No HTML content available for export")
        
        # Validate HTML content
        if not html_content.strip().startswith('<!DOCTYPE html>'):
            raise HTTPException(status_code=400, detail="Invalid HTML content")
        
        # Log export
        logger.info(
            "HTML exported",
            session_id=request.session_id,
            content_length=len(html_content)
        )
        
        # Return HTML file
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": "attachment; filename=generated.html"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export failed", session_id=request.session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Export failed")