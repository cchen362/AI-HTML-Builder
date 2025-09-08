"""
Analytics Service

Handles collection, storage, and retrieval of analytics data for the AI HTML Builder.
Tracks response times, token usage, session patterns, and output classifications.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import structlog
from ..models.analytics import AnalyticsEvent, SessionSummary, SystemStats, OutputType, RequestType
from ..core.config import settings
from .redis_service import redis_service

logger = structlog.get_logger()

class AnalyticsService:
    """Service for managing analytics data collection and retrieval"""
    
    def __init__(self):
        # Redis key prefixes
        self.EVENT_PREFIX = "analytics:event"
        self.SESSION_PREFIX = "analytics:session"
        self.STATS_PREFIX = "analytics:stats"
        
        # Data retention (7 days default)
        self.EVENT_TTL = 7 * 24 * 3600  # 7 days in seconds
        self.SESSION_TTL = 7 * 24 * 3600
        
        logger.info("Analytics service initialized")
    
    async def record_event(self, event: AnalyticsEvent) -> bool:
        """Record a new analytics event"""
        try:
            # Store individual event
            event_key = f"{self.EVENT_PREFIX}:{event.session_id}:{event.event_id}"
            event_data = event.model_dump_json()
            
            if redis_service.use_memory and redis_service.memory_store:
                # Memory store implementation
                await self._store_event_memory(event_key, event_data)
            else:
                # Redis implementation
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    redis_service.redis_client.setex,
                    event_key,
                    self.EVENT_TTL,
                    event_data
                )
            
            # Update session aggregates
            await self._update_session_stats(event)
            
            logger.info(
                "Analytics event recorded",
                session_id=event.session_id,
                event_id=event.event_id,
                output_type=event.output_type,
                response_time=event.response_time_ms,
                tokens=event.total_tokens
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to record analytics event", error=str(e), session_id=event.session_id)
            return False
    
    async def get_session_events(self, session_id: str) -> List[AnalyticsEvent]:
        """Get all analytics events for a session"""
        try:
            if redis_service.use_memory:
                return await self._get_session_events_memory(session_id)
            
            # Redis implementation
            pattern = f"{self.EVENT_PREFIX}:{session_id}:*"
            loop = asyncio.get_event_loop()
            keys = await loop.run_in_executor(None, redis_service.redis_client.keys, pattern)
            
            events = []
            for key in keys:
                data = await loop.run_in_executor(None, redis_service.redis_client.get, key)
                if data:
                    event_dict = json.loads(data)
                    events.append(AnalyticsEvent(**event_dict))
            
            # Sort by timestamp
            events.sort(key=lambda e: e.timestamp)
            return events
            
        except Exception as e:
            logger.error("Failed to retrieve session events", session_id=session_id, error=str(e))
            return []
    
    async def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """Get analytics summary for a session"""
        try:
            events = await self.get_session_events(session_id)
            if not events:
                return None
            
            return self._calculate_session_summary(session_id, events)
            
        except Exception as e:
            logger.error("Failed to get session summary", session_id=session_id, error=str(e))
            return None
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get list of all sessions with basic stats"""
        try:
            if redis_service.use_memory:
                return await self._get_all_sessions_memory()
            
            # Get all session keys
            pattern = f"{self.EVENT_PREFIX}:*:*"
            loop = asyncio.get_event_loop()
            keys = await loop.run_in_executor(None, redis_service.redis_client.keys, pattern)
            
            # Extract unique session IDs
            session_ids = set()
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 3:
                    session_ids.add(parts[2])
            
            # Get summaries for each session
            sessions = []
            for session_id in session_ids:
                summary = await self.get_session_summary(session_id)
                if summary:
                    sessions.append({
                        "session_id": session_id,
                        "created_at": summary.created_at,
                        "last_activity": summary.last_activity,
                        "duration_minutes": round(summary.duration_seconds / 60, 1),
                        "iterations": summary.total_iterations,
                        "success_rate": round(summary.successful_iterations / max(summary.total_iterations, 1) * 100, 1),
                        "total_tokens": summary.total_tokens,
                        "avg_response_time": round(summary.avg_response_time_ms / 1000, 1),
                        "output_types": summary.output_types_created,
                        "final_output": summary.final_output_type
                    })
            
            # Sort by last activity (most recent first)
            sessions.sort(key=lambda s: s["last_activity"], reverse=True)
            return sessions
            
        except Exception as e:
            logger.error("Failed to get all sessions", error=str(e))
            return []
    
    async def get_system_stats(self, days: int = 7) -> SystemStats:
        """Get overall system statistics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get all sessions in timeframe
            all_sessions = await self.get_all_sessions()
            filtered_sessions = [
                s for s in all_sessions 
                if s["last_activity"] >= start_date
            ]
            
            if not filtered_sessions:
                return self._empty_system_stats(start_date, end_date)
            
            # Calculate aggregated statistics
            total_iterations = sum(s["iterations"] for s in filtered_sessions)
            total_tokens = sum(s["total_tokens"] for s in filtered_sessions)
            total_duration = sum(s["duration_minutes"] for s in filtered_sessions)
            
            # Output type distribution
            output_type_counts = defaultdict(int)
            request_type_counts = defaultdict(int)
            response_times = []
            
            for session_data in filtered_sessions:
                # Get detailed events for this session
                events = await self.get_session_events(session_data["session_id"])
                for event in events:
                    output_type_counts[event.output_type] += 1
                    request_type_counts[event.request_type] += 1
                    if event.response_time_ms:
                        response_times.append(event.response_time_ms)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            success_rate = sum(s["success_rate"] for s in filtered_sessions) / len(filtered_sessions)
            avg_iterations = total_iterations / len(filtered_sessions) if filtered_sessions else 0
            
            return SystemStats(
                start_date=start_date,
                end_date=end_date,
                total_sessions=len(filtered_sessions),
                active_sessions=len([s for s in filtered_sessions if s["last_activity"] > end_date - timedelta(hours=1)]),
                avg_session_duration_minutes=total_duration / len(filtered_sessions) if filtered_sessions else 0,
                total_iterations=total_iterations,
                total_tokens_used=total_tokens,
                avg_response_time_ms=avg_response_time,
                output_type_distribution=dict(output_type_counts),
                request_type_distribution=dict(request_type_counts),
                success_rate=success_rate,
                avg_iterations_per_session=avg_iterations,
                most_common_output_types=sorted(output_type_counts.keys(), key=output_type_counts.get, reverse=True)[:5],
                peak_usage_hours=self._calculate_peak_hours(filtered_sessions)
            )
            
        except Exception as e:
            logger.error("Failed to get system stats", error=str(e))
            return self._empty_system_stats(datetime.utcnow() - timedelta(days=days), datetime.utcnow())
    
    def _calculate_session_summary(self, session_id: str, events: List[AnalyticsEvent]) -> SessionSummary:
        """Calculate session summary from events"""
        if not events:
            raise ValueError("No events provided for session summary")
        
        # Basic session info
        created_at = min(event.timestamp for event in events)
        last_activity = max(event.timestamp for event in events)
        duration_seconds = int((last_activity - created_at).total_seconds())
        
        # Success/failure counts
        successful = sum(1 for event in events if event.success)
        failed = len(events) - successful
        
        # Content metrics
        output_types = list(set(event.output_type for event in events))
        total_input_length = sum(event.user_input_length for event in events)
        total_output_length = sum(event.output_length for event in events)
        
        # Performance metrics
        response_times = [event.response_time_ms for event in events if event.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        total_response_time = sum(response_times)
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Token metrics
        input_tokens = sum(event.input_tokens or 0 for event in events)
        output_tokens = sum(event.output_tokens or 0 for event in events)
        total_tokens = input_tokens + output_tokens
        avg_tokens = total_tokens / len(events) if events else 0
        
        # Request type counts
        creation_count = sum(1 for event in events if event.request_type == RequestType.CREATION)
        modification_count = sum(1 for event in events if event.request_type == RequestType.MODIFICATION)
        clarification_count = sum(1 for event in events if event.request_type == RequestType.CLARIFICATION)
        
        # Final output (last successful event)
        final_output_type = None
        final_html_title = None
        for event in reversed(events):
            if event.success and event.output_type != OutputType.FALLBACK:
                final_output_type = event.output_type
                final_html_title = event.html_title
                break
        
        return SessionSummary(
            session_id=session_id,
            created_at=created_at,
            last_activity=last_activity,
            duration_seconds=duration_seconds,
            total_iterations=len(events),
            successful_iterations=successful,
            failed_iterations=failed,
            output_types_created=output_types,
            total_user_input_length=total_input_length,
            total_output_length=total_output_length,
            avg_response_time_ms=avg_response_time,
            total_response_time_ms=total_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_tokens=total_tokens,
            avg_tokens_per_iteration=avg_tokens,
            creation_requests=creation_count,
            modification_requests=modification_count,
            clarification_requests=clarification_count,
            final_output_type=final_output_type,
            final_html_title=final_html_title
        )
    
    def _empty_system_stats(self, start_date: datetime, end_date: datetime) -> SystemStats:
        """Return empty system stats"""
        return SystemStats(
            start_date=start_date,
            end_date=end_date,
            total_sessions=0,
            active_sessions=0,
            avg_session_duration_minutes=0,
            total_iterations=0,
            total_tokens_used=0,
            avg_response_time_ms=0,
            output_type_distribution={},
            request_type_distribution={},
            success_rate=0,
            avg_iterations_per_session=0,
            most_common_output_types=[],
            peak_usage_hours=[]
        )
    
    def _calculate_peak_hours(self, sessions: List[Dict[str, Any]]) -> List[int]:
        """Calculate peak usage hours from sessions"""
        hour_counts = defaultdict(int)
        for session in sessions:
            hour = session["last_activity"].hour
            hour_counts[hour] += 1
        
        # Return top 3 peak hours
        return sorted(hour_counts.keys(), key=hour_counts.get, reverse=True)[:3]
    
    async def _update_session_stats(self, event: AnalyticsEvent):
        """Update aggregated session statistics"""
        try:
            # For now, we rely on real-time calculation
            # In the future, we could maintain cached session summaries
            pass
        except Exception as e:
            logger.warning("Failed to update session stats", error=str(e))
    
    async def _store_event_memory(self, key: str, data: str):
        """Store event in memory store (fallback)"""
        # For memory store implementation
        if hasattr(redis_service.memory_store, 'analytics_events'):
            redis_service.memory_store.analytics_events[key] = data
        else:
            redis_service.memory_store.analytics_events = {key: data}
    
    async def _get_session_events_memory(self, session_id: str) -> List[AnalyticsEvent]:
        """Get session events from memory store"""
        events = []
        if hasattr(redis_service.memory_store, 'analytics_events'):
            for key, data in redis_service.memory_store.analytics_events.items():
                if f":{session_id}:" in key:
                    event_dict = json.loads(data)
                    events.append(AnalyticsEvent(**event_dict))
        
        events.sort(key=lambda e: e.timestamp)
        return events
    
    async def _get_all_sessions_memory(self) -> List[Dict[str, Any]]:
        """Get all sessions from memory store"""
        session_ids = set()
        if hasattr(redis_service.memory_store, 'analytics_events'):
            for key in redis_service.memory_store.analytics_events.keys():
                parts = key.split(":")
                if len(parts) >= 3:
                    session_ids.add(parts[2])
        
        sessions = []
        for session_id in session_ids:
            summary = await self.get_session_summary(session_id)
            if summary:
                sessions.append({
                    "session_id": session_id,
                    "created_at": summary.created_at,
                    "last_activity": summary.last_activity,
                    "duration_minutes": round(summary.duration_seconds / 60, 1),
                    "iterations": summary.total_iterations,
                    "success_rate": round(summary.successful_iterations / max(summary.total_iterations, 1) * 100, 1),
                    "total_tokens": summary.total_tokens,
                    "avg_response_time": round(summary.avg_response_time_ms / 1000, 1),
                    "output_types": summary.output_types_created,
                    "final_output": summary.final_output_type
                })
        
        sessions.sort(key=lambda s: s["last_activity"], reverse=True)
        return sessions

# Global analytics service instance
analytics_service = AnalyticsService()