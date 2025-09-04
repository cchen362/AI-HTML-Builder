from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
import json
import asyncio
import structlog
from datetime import datetime
from ..services.redis_service import redis_service
from ..services.llm_service import llm_service
from ..models.session import Session
from ..models.schemas import WebSocketMessage, MessageType
from ..core.config import settings

logger = structlog.get_logger()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, str] = {}  # session_id -> connection_id
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection and register session"""
        await websocket.accept()
        
        connection_id = f"{session_id}_{int(datetime.utcnow().timestamp())}"
        self.active_connections[connection_id] = websocket
        self.session_connections[session_id] = connection_id
        
        # Register in Redis
        client_info = {
            "client_ip": websocket.client.host if websocket.client else "unknown"
        }
        await redis_service.register_connection(session_id, client_info)
        
        logger.info("WebSocket connected", session_id=session_id, connection_id=connection_id)
        return connection_id
    
    def disconnect(self, session_id: str):
        """Remove connection"""
        connection_id = self.session_connections.get(session_id)
        if connection_id and connection_id in self.active_connections:
            del self.active_connections[connection_id]
            del self.session_connections[session_id]
        
        # Unregister from Redis
        asyncio.create_task(redis_service.unregister_connection(session_id))
        
        logger.info("WebSocket disconnected", session_id=session_id)
    
    async def send_personal_message(self, message: dict, session_id: str):
        """Send message to specific session"""
        connection_id = self.session_connections.get(session_id)
        if connection_id and connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error("Failed to send message", session_id=session_id, error=str(e))
                self.disconnect(session_id)
                return False
        return False

# Global connection manager
manager = ConnectionManager()

class WebSocketHandler:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.session: Session = None
        self.connection_id: str = None
    
    async def handle_connection(self):
        """Main WebSocket connection handler"""
        try:
            # Validate and get/create session
            self.session = await self._get_or_create_session()
            
            # Connect WebSocket
            self.connection_id = await manager.connect(self.websocket, self.session_id)
            
            # Send initial session state
            await self._send_session_sync()
            
            # Message loop
            while True:
                try:
                    # Receive message from client
                    data = await self.websocket.receive_text()
                    message_data = json.loads(data)
                    
                    # Process message
                    await self._process_message(message_data)
                    
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await self._send_error("Invalid message format")
                except Exception as e:
                    logger.error("Message processing error", session_id=self.session_id, error=str(e))
                    await self._send_error("Message processing failed")
                    
        except Exception as e:
            logger.error("WebSocket connection error", session_id=self.session_id, error=str(e))
        finally:
            manager.disconnect(self.session_id)
    
    async def _get_or_create_session(self) -> Session:
        """Get existing session or create new one"""
        session = await redis_service.get_session(self.session_id)
        
        if not session:
            # Create new session
            session = Session.create_new()
            session.session_id = self.session_id  # Use provided session ID
            await redis_service.create_session(session)
            logger.info("New session created", session_id=self.session_id)
        else:
            logger.info("Existing session found", session_id=self.session_id)
        
        return session
    
    async def _send_session_sync(self):
        """Send current session state to client"""
        sync_message = {
            "type": "sync",
            "payload": {
                "session_id": self.session.session_id,
                "messages": self.session.messages,
                "current_html": self.session.current_html,
                "iteration_count": self.session.iteration_count,
                "split_position": self.session.split_position
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(sync_message, self.session_id)
    
    async def _process_message(self, message_data: dict):
        """Process incoming WebSocket message"""
        message_type = message_data.get("type")
        
        if message_type == "chat":
            await self._handle_chat_message(message_data)
        elif message_type == "sync":
            await self._send_session_sync()
        else:
            await self._send_error(f"Unknown message type: {message_type}")
    
    async def _handle_chat_message(self, message_data: dict):
        """Handle chat message and generate HTML response"""
        try:
            content = message_data.get("content", "")
            attachments = message_data.get("attachments", [])
            
            if not content.strip() and not attachments:
                await self._send_error("Empty message")
                return
            
            # Check rate limiting
            if not await self._check_rate_limit():
                await self._send_error("Rate limit exceeded. Please wait.")
                return
            
            # Check iteration limit
            if self.session.iteration_count >= 15:
                await self._send_error("Maximum iterations reached for this session")
                return
            
            # Add user message to session
            user_message = {
                "type": "chat",
                "content": content,
                "attachments": attachments,
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "user"
            }
            self.session.add_message(user_message)
            
            # Send status update
            await self._send_status("Processing your request...", 10)
            
            # Prepare input for LLM
            llm_input = content
            if attachments:
                llm_input = f"{content}\n\nAttached content:\n" + "\n\n".join(attachments)
            
            # Send status update
            await self._send_status("Generating HTML...", 50)
            
            # Generate HTML using LLM service
            html_output = await llm_service.generate_html(
                llm_input,
                self.session.messages
            )
            
            # Add assistant message to session
            assistant_message = {
                "type": "update",
                "html_output": html_output,
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "assistant"
            }
            self.session.add_message(assistant_message)
            self.session.update_html(html_output)
            self.session.increment_iteration()
            
            # Save session to Redis
            await redis_service.update_session(self.session)
            
            # Send HTML update to client
            await self._send_html_update(html_output)
            
            # Send completion status
            await self._send_status("Complete!", 100)
            
        except Exception as e:
            logger.error("Chat message handling failed", session_id=self.session_id, error=str(e))
            await self._send_error("Failed to process message")
    
    async def _check_rate_limit(self) -> bool:
        """Check if session is within rate limits"""
        current_time = datetime.utcnow().timestamp()
        rate_limit = self.session.rate_limit
        
        # Reset window if expired
        if current_time - rate_limit.get("window_start", 0) > settings.rate_limit_window:
            rate_limit["requests"] = 0
            rate_limit["window_start"] = current_time
        
        # Check limit
        if rate_limit.get("requests", 0) >= settings.rate_limit_requests:
            return False
        
        # Increment counter
        rate_limit["requests"] = rate_limit.get("requests", 0) + 1
        return True
    
    async def _send_html_update(self, html_output: str):
        """Send HTML update to client"""
        update_message = {
            "type": "update",
            "payload": {
                "html_output": html_output,
                "iteration": self.session.iteration_count
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(update_message, self.session_id)
    
    async def _send_status(self, message: str, progress: int):
        """Send status update to client"""
        status_message = {
            "type": "status",
            "payload": {
                "message": message,
                "progress": progress
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(status_message, self.session_id)
    
    async def _send_error(self, error_message: str, recoverable: bool = True):
        """Send error message to client"""
        error_msg = {
            "type": "error",
            "payload": {
                "error": error_message,
                "recoverable": recoverable
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(error_msg, self.session_id)

# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    handler = WebSocketHandler(websocket, session_id)
    await handler.handle_connection()