from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class Session(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    iteration_count: int = 0
    messages: List[Dict[str, Any]] = []
    current_html: Optional[str] = None
    split_position: int = 50
    rate_limit: Dict[str, Any] = {"requests": 0, "window_start": 0}
    
    @classmethod
    def create_new(cls) -> "Session":
        now = datetime.utcnow()
        return cls(
            session_id=str(uuid.uuid4()),
            created_at=now,
            last_activity=now
        )
    
    def update_activity(self):
        self.last_activity = datetime.utcnow()
    
    def add_message(self, message: Dict[str, Any]):
        self.messages.append(message)
        self.update_activity()
    
    def increment_iteration(self):
        self.iteration_count += 1
        self.update_activity()
    
    def update_html(self, html_content: str):
        self.current_html = html_content
        self.update_activity()
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        time_diff = datetime.utcnow() - self.last_activity
        return time_diff.total_seconds() > timeout_seconds