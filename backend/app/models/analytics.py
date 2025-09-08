"""
Analytics Models

Data models for tracking and storing analytics events in the AI HTML Builder.
Captures response times, token usage, session iterations, and output classifications.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class OutputType(str, Enum):
    """Classification of generated content types"""
    LANDING_PAGE = "landing-page"
    DOCUMENTATION = "documentation" 
    NEWSLETTER = "newsletter"
    IMPACT_ASSESSMENT = "impact-assessment"
    DASHBOARD = "dashboard"
    PRESENTATION = "presentation"
    PORTFOLIO = "portfolio"
    ARTICLE = "article"
    CUSTOM = "custom"
    FALLBACK = "fallback"

class RequestType(str, Enum):
    """Type of user request"""
    CREATION = "creation"      # New content creation
    MODIFICATION = "modification"  # Editing existing content
    CLARIFICATION = "clarification"  # Questions/clarifications

class AnalyticsEvent(BaseModel):
    """Single analytics event capturing all relevant metrics"""
    
    # Event identification
    event_id: str
    session_id: str
    timestamp: datetime
    
    # Session context
    iteration_number: int
    total_iterations: int
    
    # User input analysis
    user_input: str
    user_input_length: int
    request_type: RequestType
    
    # Processing metrics
    response_time_ms: int  # Total processing time
    claude_api_time_ms: Optional[int] = None  # Claude API specific time
    
    # Token usage
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Output analysis
    output_type: OutputType
    output_length: int
    html_title: Optional[str] = None
    
    # Change detection (for modifications)
    is_modification: bool = False
    changes_detected: List[str] = []
    
    # Metadata
    model_used: str = "claude-sonnet-4-20250514"
    success: bool = True
    error_message: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = {}

class SessionSummary(BaseModel):
    """Summary analytics for a complete session"""
    
    session_id: str
    created_at: datetime
    last_activity: datetime
    duration_seconds: int
    
    # Interaction metrics
    total_iterations: int
    successful_iterations: int
    failed_iterations: int
    
    # Content metrics
    output_types_created: List[OutputType]
    total_user_input_length: int
    total_output_length: int
    
    # Performance metrics
    avg_response_time_ms: float
    total_response_time_ms: int
    min_response_time_ms: int
    max_response_time_ms: int
    
    # Token usage
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_tokens_per_iteration: float
    
    # Request patterns
    creation_requests: int
    modification_requests: int
    clarification_requests: int
    
    # Final output
    final_output_type: Optional[OutputType] = None
    final_html_title: Optional[str] = None

class SystemStats(BaseModel):
    """Overall system usage statistics"""
    
    # Time range
    start_date: datetime
    end_date: datetime
    
    # Session metrics
    total_sessions: int
    active_sessions: int
    avg_session_duration_minutes: float
    
    # Usage metrics
    total_iterations: int
    total_tokens_used: int
    avg_response_time_ms: float
    
    # Content breakdown
    output_type_distribution: Dict[OutputType, int]
    request_type_distribution: Dict[RequestType, int]
    
    # Performance metrics
    success_rate: float
    avg_iterations_per_session: float
    
    # Popular patterns
    most_common_output_types: List[OutputType]
    peak_usage_hours: List[int]  # Hours of day (0-23)