from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    CHAT = "chat"
    UPDATE = "update"
    ERROR = "error"
    STATUS = "status"
    SYNC = "sync"

class FileInfo(BaseModel):
    name: str
    size: int
    type: str

class Message(BaseModel):
    type: MessageType
    content: Optional[str] = None
    html_output: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    timestamp: datetime
    sender: str = "user"  # or "assistant"

class ChatRequest(BaseModel):
    content: str
    attachments: Optional[List[str]] = None

class WebSocketMessage(BaseModel):
    type: MessageType
    session_id: str
    payload: Dict[str, Any]
    timestamp: int

class UploadResponse(BaseModel):
    extracted_text: str
    file_info: FileInfo

class ExportRequest(BaseModel):
    session_id: str
    html_content: str

class HealthResponse(BaseModel):
    status: str
    timestamp: int
    redis: str
    version: str