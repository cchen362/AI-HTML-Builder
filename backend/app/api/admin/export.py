"""
Admin Export Endpoints

Handles CSV data export functionality for analytics data.
"""

import csv
import io
from fastapi import APIRouter, HTTPException, status, Depends, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timedelta
import structlog
from ...middleware.auth import require_admin
from ...services.analytics_service import analytics_service

logger = structlog.get_logger()

router = APIRouter()

@router.get("/csv")
async def export_analytics_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    session_id: Optional[str] = Query(None, description="Specific session ID"),
    output_type: Optional[str] = Query(None, description="Filter by output type"),
    admin_data: dict = Depends(require_admin)
):
    """Export analytics data as CSV"""
    try:
        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date + "T23:59:59")
        
        # Get data to export
        if session_id:
            # Export specific session
            events = await analytics_service.get_session_events(session_id)
        else:
            # Export all sessions
            all_sessions = await analytics_service.get_all_sessions()
            events = []
            
            for session_data in all_sessions:
                # Apply date filter
                if start_dt and session_data["last_activity"] < start_dt:
                    continue
                if end_dt and session_data["created_at"] > end_dt:
                    continue
                
                session_events = await analytics_service.get_session_events(session_data["session_id"])
                events.extend(session_events)
        
        # Apply output type filter
        if output_type:
            events = [e for e in events if e.output_type == output_type]
        
        # Apply date filter to events if no session filter
        if not session_id and (start_dt or end_dt):
            if start_dt:
                events = [e for e in events if e.timestamp >= start_dt]
            if end_dt:
                events = [e for e in events if e.timestamp <= end_dt]
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        # Generate CSV content
        csv_content = _generate_csv_content(events)
        
        # Generate filename
        filename = _generate_filename(start_date, end_date, session_id, output_type)
        
        logger.info("Admin dashboard: CSV export generated", 
                   events_count=len(events),
                   filename=filename,
                   filters={
                       "start_date": start_date,
                       "end_date": end_date,
                       "session_id": session_id,
                       "output_type": output_type
                   },
                   admin_id=admin_data.get("sub"))
        
        # Return CSV as streaming response
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to export CSV", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSV export"
        )

@router.get("/session-summary-csv")
async def export_session_summary_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    admin_data: dict = Depends(require_admin)
):
    """Export session summaries as CSV"""
    try:
        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date + "T23:59:59")
        
        # Get all sessions
        all_sessions = await analytics_service.get_all_sessions()
        
        # Apply date filters
        filtered_sessions = []
        for session_data in all_sessions:
            if start_dt and session_data["last_activity"] < start_dt:
                continue
            if end_dt and session_data["created_at"] > end_dt:
                continue
            filtered_sessions.append(session_data)
        
        # Generate CSV content for session summaries
        csv_content = _generate_session_summary_csv(filtered_sessions)
        
        # Generate filename
        filename = f"session_summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        if start_date and end_date:
            filename = f"session_summaries_{start_date}_to_{end_date}.csv"
        
        logger.info("Admin dashboard: session summary CSV export generated", 
                   sessions_count=len(filtered_sessions),
                   filename=filename,
                   admin_id=admin_data.get("sub"))
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to export session summary CSV", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate session summary CSV export"
        )

def _generate_csv_content(events: List) -> str:
    """Generate CSV content from analytics events"""
    output = io.StringIO()
    
    # CSV headers
    fieldnames = [
        'timestamp',
        'session_id',
        'iteration',
        'user_input_length',
        'request_type',
        'response_time_ms',
        'claude_api_time_ms',
        'input_tokens',
        'output_tokens',
        'total_tokens',
        'output_type',
        'output_length',
        'html_title',
        'is_modification',
        'changes_count',
        'success',
        'error_message',
        'model_used'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write event data
    for event in events:
        writer.writerow({
            'timestamp': event.timestamp.isoformat(),
            'session_id': event.session_id,
            'iteration': event.iteration_number,
            'user_input_length': event.user_input_length,
            'request_type': event.request_type,
            'response_time_ms': event.response_time_ms,
            'claude_api_time_ms': event.claude_api_time_ms,
            'input_tokens': event.input_tokens or 0,
            'output_tokens': event.output_tokens or 0,
            'total_tokens': event.total_tokens or 0,
            'output_type': event.output_type,
            'output_length': event.output_length,
            'html_title': event.html_title or '',
            'is_modification': event.is_modification,
            'changes_count': len(event.changes_detected),
            'success': event.success,
            'error_message': event.error_message or '',
            'model_used': event.model_used
        })
    
    return output.getvalue()

def _generate_session_summary_csv(sessions: List) -> str:
    """Generate CSV content from session summaries"""
    output = io.StringIO()
    
    # CSV headers for session summaries
    fieldnames = [
        'session_id',
        'created_at',
        'last_activity',
        'duration_minutes',
        'total_iterations',
        'success_rate',
        'total_tokens',
        'avg_response_time_seconds',
        'output_types',
        'final_output_type',
        'user_input_total_length',
        'avg_tokens_per_iteration'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write session data
    for session in sessions:
        writer.writerow({
            'session_id': session['session_id'],
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'duration_minutes': session['duration_minutes'],
            'total_iterations': session['iterations'],
            'success_rate': session['success_rate'],
            'total_tokens': session['total_tokens'],
            'avg_response_time_seconds': session['avg_response_time'],
            'output_types': ','.join([str(ot) for ot in session['output_types']]),
            'final_output_type': session['final_output'] or '',
            'user_input_total_length': 0,  # Would need to calculate from events
            'avg_tokens_per_iteration': round(session['total_tokens'] / max(session['iterations'], 1), 1)
        })
    
    return output.getvalue()

def _generate_filename(start_date: Optional[str], end_date: Optional[str], 
                      session_id: Optional[str], output_type: Optional[str]) -> str:
    """Generate appropriate filename for CSV export"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if session_id:
        return f"analytics_{session_id}_{timestamp}.csv"
    
    filename_parts = ["analytics"]
    
    if output_type:
        filename_parts.append(output_type.replace("-", "_"))
    
    if start_date and end_date:
        filename_parts.append(f"{start_date}_to_{end_date}")
    elif start_date:
        filename_parts.append(f"from_{start_date}")
    elif end_date:
        filename_parts.append(f"until_{end_date}")
    else:
        filename_parts.append(timestamp)
    
    return "_".join(filename_parts) + ".csv"