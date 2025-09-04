import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import json
import structlog
from ..models.session import Session

logger = structlog.get_logger()

class MemoryStore:
    """In-memory store for development when Redis is not available"""
    
    def __init__(self):
        self.sessions: Dict[str, str] = {}  # session_id -> json_data
        self.connections: Dict[str, Dict[str, Any]] = {}  # session_id -> connection_info
        self.cleanup_task = None
    
    async def connect(self):
        """Initialize memory store"""
        logger.info("Memory store initialized (Redis alternative)")
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def disconnect(self):
        """Close memory store"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        self.sessions.clear()
        self.connections.clear()
        logger.info("Memory store closed")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup task error", error=str(e))
    
    def _session_key(self, session_id: str) -> str:
        """Generate key for session"""
        return f"session:{session_id}"
    
    async def create_session(self, session: Session) -> bool:
        """Create new session in memory"""
        try:
            session_data = session.model_dump_json()
            key = self._session_key(session.session_id)
            self.sessions[key] = session_data
            
            logger.info("Session created in memory", session_id=session.session_id)
            return True
            
        except Exception as e:
            logger.error("Failed to create session", session_id=session.session_id, error=str(e))
            return False
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session from memory"""
        try:
            key = self._session_key(session_id)
            data = self.sessions.get(key)
            
            if data:
                session_dict = json.loads(data)
                session = Session(**session_dict)
                
                # Check if session is expired
                if session.is_expired():
                    await self.delete_session(session_id)
                    return None
                    
                return session
            
            return None
            
        except Exception as e:
            logger.error("Failed to get session", session_id=session_id, error=str(e))
            return None
    
    async def update_session(self, session: Session) -> bool:
        """Update existing session in memory"""
        try:
            session.update_activity()
            session_data = session.model_dump_json()
            key = self._session_key(session.session_id)
            self.sessions[key] = session_data
            
            return True
            
        except Exception as e:
            logger.error("Failed to update session", session_id=session.session_id, error=str(e))
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory"""
        try:
            key = self._session_key(session_id)
            if key in self.sessions:
                del self.sessions[key]
            
            # Also remove connection if exists
            if session_id in self.connections:
                del self.connections[session_id]
            
            logger.info("Session deleted from memory", session_id=session_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))
            return False
    
    async def register_connection(self, session_id: str, client_info: Dict[str, Any]) -> bool:
        """Register WebSocket connection"""
        try:
            connection_data = {
                "connected_at": datetime.utcnow().isoformat(),
                "last_ping": datetime.utcnow().isoformat(),
                **client_info
            }
            
            self.connections[session_id] = connection_data
            return True
            
        except Exception as e:
            logger.error("Failed to register connection", session_id=session_id, error=str(e))
            return False
    
    async def unregister_connection(self, session_id: str) -> bool:
        """Unregister WebSocket connection"""
        try:
            if session_id in self.connections:
                del self.connections[session_id]
            return True
            
        except Exception as e:
            logger.error("Failed to unregister connection", session_id=session_id, error=str(e))
            return False
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            expired_keys = []
            
            for key, data in self.sessions.items():
                try:
                    session_dict = json.loads(data)
                    session = Session(**session_dict)
                    if session.is_expired():
                        expired_keys.append(key)
                        # Extract session_id from key
                        session_id = key.replace("session:", "")
                        if session_id in self.connections:
                            del self.connections[session_id]
                except:
                    # If we can't parse the session, mark it for deletion
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.sessions[key]
                
            if expired_keys:
                logger.info("Cleaned up expired sessions", count=len(expired_keys))
            
        except Exception as e:
            logger.error("Session cleanup failed", error=str(e))
    
    async def is_healthy(self) -> bool:
        """Check memory store health"""
        return True