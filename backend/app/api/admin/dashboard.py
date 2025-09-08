"""
Admin Dashboard API Endpoints

Provides data endpoints for the admin dashboard to view analytics and session information.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
from ...middleware.auth import require_admin
from ...services.analytics_service import analytics_service
from ...models.analytics import SessionSummary, SystemStats

logger = structlog.get_logger()

router = APIRouter()

@router.get("/sessions")
async def get_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_data: dict = Depends(require_admin)
):
    """Get list of all sessions with analytics"""
    try:
        all_sessions = await analytics_service.get_all_sessions()
        
        # Apply pagination
        total_sessions = len(all_sessions)
        sessions = all_sessions[offset:offset + limit]
        
        logger.info("Admin dashboard: sessions retrieved", 
                   total=total_sessions, 
                   returned=len(sessions),
                   admin_id=admin_data.get("sub"))
        
        return {
            "sessions": sessions,
            "total": total_sessions,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_sessions
        }
        
    except Exception as e:
        logger.error("Failed to retrieve sessions for admin", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )

@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    admin_data: dict = Depends(require_admin)
):
    """Get detailed analytics for a specific session"""
    try:
        # Get session summary
        summary = await analytics_service.get_session_summary(session_id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get individual events
        events = await analytics_service.get_session_events(session_id)
        
        # Format events for frontend
        formatted_events = []
        for event in events:
            formatted_events.append({
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "iteration": event.iteration_number,
                "user_input": event.user_input[:200] + "..." if len(event.user_input) > 200 else event.user_input,
                "user_input_length": event.user_input_length,
                "request_type": event.request_type,
                "response_time_ms": event.response_time_ms,
                "claude_api_time_ms": event.claude_api_time_ms,
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "total_tokens": event.total_tokens,
                "output_type": event.output_type,
                "output_length": event.output_length,
                "html_title": event.html_title,
                "is_modification": event.is_modification,
                "changes_detected": event.changes_detected,
                "success": event.success,
                "error_message": event.error_message
            })
        
        logger.info("Admin dashboard: session detail retrieved", 
                   session_id=session_id,
                   events_count=len(events),
                   admin_id=admin_data.get("sub"))
        
        return {
            "session": summary.model_dump(),
            "events": formatted_events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve session detail", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session details"
        )

@router.get("/stats")
async def get_system_stats(
    days: int = Query(7, ge=1, le=30),
    admin_data: dict = Depends(require_admin)
):
    """Get overall system statistics"""
    try:
        stats = await analytics_service.get_system_stats(days=days)
        
        logger.info("Admin dashboard: system stats retrieved", 
                   days=days,
                   total_sessions=stats.total_sessions,
                   admin_id=admin_data.get("sub"))
        
        return {
            "stats": stats.model_dump(),
            "period_days": days
        }
        
    except Exception as e:
        logger.error("Failed to retrieve system stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )

@router.get("/overview")
async def get_dashboard_overview(
    admin_data: dict = Depends(require_admin)
):
    """Get dashboard overview with key metrics"""
    try:
        # Get recent sessions (last 24 hours)
        all_sessions = await analytics_service.get_all_sessions()
        recent_sessions = [
            s for s in all_sessions 
            if s["last_activity"] > datetime.utcnow() - timedelta(hours=24)
        ]
        
        # Get 7-day stats
        stats = await analytics_service.get_system_stats(days=7)
        
        # Calculate additional metrics
        total_sessions_ever = len(all_sessions)
        active_sessions_last_hour = len([
            s for s in all_sessions 
            if s["last_activity"] > datetime.utcnow() - timedelta(hours=1)
        ])
        
        # Recent activity (last 5 sessions)
        recent_activity = all_sessions[:5]
        
        # Popular output types (last 7 days)
        popular_outputs = []
        for output_type, count in stats.output_type_distribution.items():
            popular_outputs.append({
                "type": output_type,
                "count": count,
                "percentage": round(count / max(stats.total_iterations, 1) * 100, 1)
            })
        popular_outputs.sort(key=lambda x: x["count"], reverse=True)
        
        logger.info("Admin dashboard: overview retrieved", 
                   total_sessions=total_sessions_ever,
                   recent_sessions=len(recent_sessions),
                   admin_id=admin_data.get("sub"))
        
        return {
            "overview": {
                "total_sessions": total_sessions_ever,
                "sessions_last_24h": len(recent_sessions),
                "active_sessions_last_hour": active_sessions_last_hour,
                "avg_response_time_ms": round(stats.avg_response_time_ms),
                "total_tokens_7d": stats.total_tokens_used,
                "success_rate": round(stats.success_rate, 1),
                "avg_iterations_per_session": round(stats.avg_iterations_per_session, 1)
            },
            "recent_activity": recent_activity,
            "popular_outputs": popular_outputs[:5],
            "stats_7d": {
                "total_iterations": stats.total_iterations,
                "avg_session_duration": round(stats.avg_session_duration_minutes, 1),
                "peak_hours": stats.peak_usage_hours
            }
        }
        
    except Exception as e:
        logger.error("Failed to retrieve dashboard overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard overview"
        )

@router.delete("/sessions/{session_id}")
async def delete_session_data(
    session_id: str,
    admin_data: dict = Depends(require_admin)
):
    """Delete analytics data for a specific session"""
    try:
        # Get events to delete
        events = await analytics_service.get_session_events(session_id)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Delete events from Redis/memory store
        deleted_count = 0
        for event in events:
            # Delete individual event keys
            event_key = f"{analytics_service.EVENT_PREFIX}:{session_id}:{event.event_id}"
            try:
                if analytics_service.redis_service.use_memory:
                    if hasattr(analytics_service.redis_service.memory_store, 'analytics_events'):
                        analytics_service.redis_service.memory_store.analytics_events.pop(event_key, None)
                else:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, analytics_service.redis_service.redis_client.delete, event_key)
                deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete event", event_id=event.event_id, error=str(e))
        
        logger.info("Admin dashboard: session data deleted", 
                   session_id=session_id,
                   events_deleted=deleted_count,
                   admin_id=admin_data.get("sub"))
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} analytics events for session {session_id}",
            "deleted_events": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete session data", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session data"
        )