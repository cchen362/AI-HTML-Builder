from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List
import json
import asyncio
import structlog
from datetime import datetime
from ..services.redis_service import redis_service
from ..services.claude_service import claude_service
from ..services.artifact_manager import artifact_manager
from ..services.analytics_service import analytics_service
from ..models.session import Session
from ..models.schemas import WebSocketMessage, MessageType
from ..models.analytics import AnalyticsEvent, OutputType, RequestType
from ..core.config import settings
import time
import uuid
import re

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
                    # Only try to send error if connection is still active
                    try:
                        await self._send_error("Message processing failed")
                    except Exception:
                        # If sending error fails, break the loop to prevent spam
                        logger.info("Connection lost, stopping message processing", session_id=self.session_id)
                        break
                    
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
        logger.info("[DEBUG] WebSocket chat message received!", session_id=self.session_id, message_type=message_data.get("type"))
        
        # Start timing for analytics
        start_time = time.time()
        event_id = str(uuid.uuid4())
        
        try:
            content = message_data.get("content", "")
            attachments = message_data.get("attachments", [])
            
            if not content.strip():
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
            
            # Determine request type for analytics
            request_type = self._classify_request_type(content, self.session.messages)
            
            # Add user message to session
            user_message = {
                "type": "chat",
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "user"
            }
            self.session.add_message(user_message)
            
            # Send thinking status for large content
            if len(content) > 1000:
                await self._send_thinking_status("I can see you've shared detailed content - analyzing with Claude Sonnet 4 for exceptional design...")
            
            # Send progress updates with Claude-powered approach
            await self._send_thinking_status("🎨 Claude Sonnet 4 analyzing your creative vision...")
            await self._send_thinking_status("✨ Designing professional layout with advanced visual hierarchy...")
            await self._send_thinking_status("🚀 Adding responsive features and polished interactions...")
            
            # Build simple context for Claude service
            current_artifact = artifact_manager.get_current_artifact(self.session_id)
            
            # Generate dual response using Claude Sonnet 4 service
            logger.info("[DEBUG] About to call claude_service.generate_dual_response", session_id=self.session_id)
            claude_start_time = time.time()
            success = True
            error_message = None
            
            try:
                dual_response = claude_service.generate_dual_response(
                    content,
                    self.session.messages,  # Pass messages directly
                    self.session_id
                )
                logger.info("Successfully received dual_response from claude_service", session_id=self.session_id)
                
                logger.info("Claude dual response generated", 
                           html_length=len(dual_response.html_output), 
                           conversation_length=len(dual_response.conversation))
                
            except Exception as claude_error:
                success = False
                error_message = str(claude_error)
                logger.error("Claude service error", error=str(claude_error), session_id=self.session_id)
                # Create fallback response
                from ..services.claude_service import DualResponse
                dual_response = DualResponse(
                    html_output=self._create_fallback_html(content),
                    conversation=f"I encountered a technical issue while processing your request '{content}'. I've created a placeholder design - please try again for a fully custom solution!",
                    metadata={"is_fallback": True}
                )
            
            claude_api_time = int((time.time() - claude_start_time) * 1000)  # ms
            
            # Create or update artifact
            if current_artifact:
                artifact = artifact_manager.update_artifact(
                    self.session_id,
                    dual_response.html_output,
                    dual_response.metadata.get('changes', []),
                    dual_response.metadata
                )
            else:
                artifact = artifact_manager.create_artifact(
                    self.session_id,
                    dual_response.html_output,
                    dual_response.metadata
                )
            
            # Add assistant message to session
            assistant_message = {
                "type": "update",
                "html_output": dual_response.html_output,
                "conversation": dual_response.conversation,
                "artifact_version": artifact.version,
                "timestamp": datetime.utcnow().isoformat(),
                "sender": "assistant"
            }
            self.session.add_message(assistant_message)
            self.session.update_html(dual_response.html_output)
            self.session.increment_iteration()
            
            # Save session to Redis
            await redis_service.update_session(self.session)
            
            # Record analytics event
            total_response_time = int((time.time() - start_time) * 1000)
            await self._record_analytics_event(
                event_id, content, request_type, total_response_time, 
                claude_api_time, dual_response, success, error_message
            )
            
            # Send dual response with artifact information
            await self._send_conversational_dual_response(
                dual_response.html_output, 
                dual_response.conversation,
                artifact
            )
            
            # Send completion status
            await self._send_status("Ready for your next request!", 100)
            
        except Exception as e:
            logger.error("Conversational chat message handling failed", session_id=self.session_id, error=str(e))
            await self._send_error("I encountered an unexpected issue. Please try again with your request.")
    
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
    
    async def _send_conversational_dual_response(self, html_output: str, conversation: str, artifact):
        """Send conversational dual response with artifact information to client"""
        logger.info("Sending conversational dual response", 
                   session_id=self.session_id,
                   html_length=len(html_output),
                   conversation_length=len(conversation),
                   artifact_version=artifact.version)
        
        update_message = {
            "type": "dual_response",
            "payload": {
                "htmlOutput": html_output,  # HTML artifact for rendering panel
                "conversation": conversation,  # Conversational response for chat
                "artifact": {
                    "id": artifact.id,
                    "version": artifact.version,
                    "title": artifact.title,
                    "type": artifact.content_type,
                    "changes": artifact.changes_from_previous or []
                },
                "iteration": self.session.iteration_count
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(update_message, self.session_id)
    
    async def _send_thinking_status(self, message: str):
        """Send thinking status update with conversational flair"""
        status_message = {
            "type": "thinking",
            "payload": {
                "message": message,
                "timestamp": int(datetime.utcnow().timestamp())
            },
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        await manager.send_personal_message(status_message, self.session_id)
    
    def _create_fallback_html(self, user_request: str) -> str:
        """Create fallback HTML when generation fails"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI HTML Builder - Processing</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 2rem; color: #152835;
        }}
        .container {{
            max-width: 600px; background: white; border-radius: 16px; padding: 3rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); text-align: center;
        }}
        .header {{
            background: linear-gradient(135deg, #003366 0%, #0066CF 100%);
            color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem;
        }}
        .header h1 {{ font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem; }}
        .request-box {{
            background: #e6f3ff; border: 2px solid #b4ebff; border-radius: 8px;
            padding: 1.5rem; margin: 1.5rem 0;
        }}
        .request-box h3 {{ color: #003366; margin-bottom: 0.75rem; }}
        .retry-button {{
            background: linear-gradient(135deg, #0066CF 0%, #003366 100%);
            color: white; padding: 1rem 2rem; border: none; border-radius: 8px;
            font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease;
        }}
        .retry-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 102, 207, 0.3); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI HTML Builder</h1>
            <p>Conversational Design Assistant</p>
        </div>
        <div class="request-box">
            <h3>Your Request</h3>
            <p>"{user_request}"</p>
        </div>
        <p>I'm working on creating something amazing for you! This is a temporary placeholder.</p>
        <button class="retry-button" onclick="location.reload()">Try Again</button>
    </div>
</body>
</html>"""
    
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
        
        # Try to send error message, if it fails the connection is likely broken
        success = await manager.send_personal_message(error_msg, self.session_id)
        if not success:
            raise Exception("Failed to send error message - connection broken")
    
    def _classify_request_type(self, content: str, message_history: list) -> RequestType:
        """Classify the type of user request for analytics"""
        content_lower = content.lower()
        
        # Check for modification keywords
        modification_words = [
            "change", "modify", "update", "adjust", "fix", "edit", "improve", 
            "enhance", "make", "add", "remove", "alter", "delete", "replace"
        ]
        
        if any(word in content_lower for word in modification_words) and len(message_history) > 1:
            return RequestType.MODIFICATION
        
        # Check for clarification keywords
        clarification_words = [
            "what", "how", "why", "explain", "clarify", "understand", 
            "meaning", "help me", "can you", "could you"
        ]
        
        if any(word in content_lower for word in clarification_words):
            return RequestType.CLARIFICATION
        
        # Default to creation for new requests
        return RequestType.CREATION
    
    def _classify_output_type(self, html_content: str, user_input: str) -> OutputType:
        """Classify the type of output generated"""
        html_lower = html_content.lower()
        input_lower = user_input.lower()
        
        # Check for specific keywords in both HTML and user input
        if any(word in html_lower or word in input_lower for word in ["assessment", "impact assessment", "analysis"]):
            return OutputType.IMPACT_ASSESSMENT
        elif any(word in html_lower or word in input_lower for word in ["landing", "hero", "landing page"]):
            return OutputType.LANDING_PAGE
        elif any(word in html_lower or word in input_lower for word in ["newsletter", "email", "campaign"]):
            return OutputType.NEWSLETTER
        elif any(word in html_lower or word in input_lower for word in ["documentation", "docs", "guide", "manual"]):
            return OutputType.DOCUMENTATION
        elif any(word in html_lower or word in input_lower for word in ["dashboard", "admin panel", "control panel"]):
            return OutputType.DASHBOARD
        elif any(word in html_lower or word in input_lower for word in ["presentation", "slides", "pitch"]):
            return OutputType.PRESENTATION
        elif any(word in html_lower or word in input_lower for word in ["portfolio", "showcase", "gallery"]):
            return OutputType.PORTFOLIO
        elif any(word in html_lower or word in input_lower for word in ["article", "blog", "post"]):
            return OutputType.ARTICLE
        elif "fallback" in html_lower or "placeholder" in html_lower:
            return OutputType.FALLBACK
        else:
            return OutputType.CUSTOM
    
    def _extract_html_title(self, html_content: str) -> str:
        """Extract title from HTML content"""
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return title_match.group(1) if title_match else "Generated Page"
    
    async def _record_analytics_event(
        self, event_id: str, user_input: str, request_type: RequestType,
        total_response_time: int, claude_api_time: int, dual_response,
        success: bool, error_message: str = None
    ):
        """Record analytics event for this interaction"""
        try:
            # Extract token usage from dual_response metadata
            input_tokens = dual_response.metadata.get("input_tokens", 0) if hasattr(dual_response, 'metadata') else 0
            output_tokens = dual_response.metadata.get("output_tokens", 0) if hasattr(dual_response, 'metadata') else 0
            total_tokens = dual_response.metadata.get("tokens_used", input_tokens + output_tokens)
            
            # Classify output type
            output_type = self._classify_output_type(dual_response.html_output, user_input)
            
            # Extract HTML title
            html_title = self._extract_html_title(dual_response.html_output)
            
            # Detect if this is a modification
            is_modification = request_type == RequestType.MODIFICATION
            changes_detected = dual_response.metadata.get("changes", []) if hasattr(dual_response, 'metadata') else []
            
            # Create analytics event
            analytics_event = AnalyticsEvent(
                event_id=event_id,
                session_id=self.session_id,
                timestamp=datetime.utcnow(),
                iteration_number=self.session.iteration_count + 1,  # Will be incremented after this
                total_iterations=self.session.iteration_count + 1,
                user_input=user_input,
                user_input_length=len(user_input),
                request_type=request_type,
                response_time_ms=total_response_time,
                claude_api_time_ms=claude_api_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                output_type=output_type,
                output_length=len(dual_response.html_output),
                html_title=html_title,
                is_modification=is_modification,
                changes_detected=changes_detected,
                success=success,
                error_message=error_message,
                model_used="claude-sonnet-4-20250514",
                metadata={
                    "user_agent": "websocket-client",
                    "has_attachments": False,  # Could be extended for file uploads
                    "session_start": self.session.created_at.isoformat()
                }
            )
            
            # Record the event
            await analytics_service.record_event(analytics_event)
            
            logger.info("Analytics event recorded", 
                       session_id=self.session_id, 
                       event_id=event_id,
                       output_type=output_type,
                       response_time=total_response_time,
                       tokens=total_tokens)
            
        except Exception as e:
            # Don't fail the main request if analytics fail
            logger.error("Failed to record analytics event", 
                        session_id=self.session_id, 
                        error=str(e))

# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    logger.info("[DEBUG WEBSOCKET ENTRY] WebSocket endpoint called!", session_id=session_id)
    handler = WebSocketHandler(websocket, session_id)
    await handler.handle_connection()