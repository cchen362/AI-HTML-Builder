import redis
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from ..models.session import Session
from ..core.config import settings
from .memory_store import MemoryStore

logger = structlog.get_logger()

class RedisService:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool = None
        self.memory_store: Optional[MemoryStore] = None
        self.use_memory = False
    
    async def connect(self):
        """Initialize Redis connection with fallback to memory store"""
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                decode_responses=True
            )
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self._ping()
            logger.info("Redis connected successfully")
            self.use_memory = False
            
        except Exception as e:
            logger.warning("Redis connection failed, falling back to memory store", error=str(e))
            # Fall back to memory store
            self.memory_store = MemoryStore()
            await self.memory_store.connect()
            self.use_memory = True
    
    async def _ping(self):
        """Test Redis connection"""
        if self.redis_client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.redis_client.ping)
    
    async def disconnect(self):
        """Close Redis connections or memory store"""
        if self.use_memory and self.memory_store:
            await self.memory_store.disconnect()
        elif self.connection_pool:
            self.connection_pool.disconnect()
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{session_id}"
    
    def _connection_key(self) -> str:
        """Generate Redis key for connections registry"""
        return "connections"
    
    async def create_session(self, session: Session) -> bool:
        """Create new session"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.create_session(session)
        
        try:
            if not self.redis_client:
                return False
            
            session_data = session.model_dump_json()
            key = self._session_key(session.session_id)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.redis_client.setex,
                key,
                settings.session_timeout,
                session_data
            )
            
            logger.info("Session created", session_id=session.session_id)
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to create session", session_id=session.session_id, error=str(e))
            return False
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.get_session(session_id)
            
        try:
            if not self.redis_client:
                return None
            
            key = self._session_key(session_id)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self.redis_client.get, key)
            
            if data:
                session_dict = json.loads(data)
                return Session(**session_dict)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get session", session_id=session_id, error=str(e))
            return None
    
    async def update_session(self, session: Session) -> bool:
        """Update existing session"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.update_session(session)
            
        try:
            if not self.redis_client:
                return False
            
            session.update_activity()
            session_data = session.model_dump_json()
            key = self._session_key(session.session_id)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.redis_client.setex,
                key,
                settings.session_timeout,
                session_data
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to update session", session_id=session.session_id, error=str(e))
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.delete_session(session_id)
            
        try:
            if not self.redis_client:
                return False
            
            key = self._session_key(session_id)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.redis_client.delete, key)
            
            logger.info("Session deleted", session_id=session_id)
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))
            return False
    
    async def register_connection(self, session_id: str, client_info: Dict[str, Any]) -> bool:
        """Register WebSocket connection"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.register_connection(session_id, client_info)
            
        try:
            if not self.redis_client:
                return False
            
            connection_data = {
                "connected_at": datetime.utcnow().isoformat(),
                "last_ping": datetime.utcnow().isoformat(),
                **client_info
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.redis_client.hset,
                self._connection_key(),
                session_id,
                json.dumps(connection_data)
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to register connection", session_id=session_id, error=str(e))
            return False
    
    async def unregister_connection(self, session_id: str) -> bool:
        """Unregister WebSocket connection"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.unregister_connection(session_id)
            
        try:
            if not self.redis_client:
                return False
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.redis_client.hdel,
                self._connection_key(),
                session_id
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to unregister connection", session_id=session_id, error=str(e))
            return False
    
    async def cleanup_expired_sessions(self):
        """Background task to clean up expired sessions"""
        if self.use_memory and self.memory_store:
            await self.memory_store.cleanup_expired_sessions()
            return
            
        try:
            if not self.redis_client:
                return
            
            # Redis handles TTL automatically, but we can add custom cleanup logic here
            logger.info("Session cleanup completed")
            
        except Exception as e:
            logger.error("Session cleanup failed", error=str(e))
    
    async def is_healthy(self) -> bool:
        """Check health"""
        if self.use_memory and self.memory_store:
            return await self.memory_store.is_healthy()
            
        try:
            await self._ping()
            return True
        except:
            return False

# Global Redis service instance
redis_service = RedisService()