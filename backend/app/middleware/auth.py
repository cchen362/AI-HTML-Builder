"""
Authentication Middleware

Handles admin authentication using JWT tokens for secure access to admin dashboard.
"""

import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
from ..core.config import settings

logger = structlog.get_logger()

class AdminAuth:
    """Admin authentication handler"""
    
    def __init__(self):
        # Admin credentials
        self.ADMIN_PASSWORD = "adminhtml"  # Updated password
        self.ADMIN_PASSWORD_HASH = self._hash_password(self.ADMIN_PASSWORD)
        
        # JWT settings
        self.JWT_SECRET = getattr(settings, 'jwt_secret', 'ai-html-builder-jwt-secret-key-2025')
        self.JWT_ALGORITHM = "HS256"
        self.TOKEN_EXPIRE_HOURS = 8  # 8 hour sessions
        
        logger.info("Admin authentication system initialized")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_admin_password(self, password: str) -> bool:
        """Verify admin password"""
        password_hash = self._hash_password(password)
        return password_hash == self.ADMIN_PASSWORD_HASH
    
    def create_admin_token(self, admin_id: str = "admin") -> str:
        """Create JWT token for admin user"""
        try:
            payload = {
                "sub": admin_id,
                "role": "admin", 
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=self.TOKEN_EXPIRE_HOURS)
            }
            
            token = jwt.encode(payload, self.JWT_SECRET, algorithm=self.JWT_ALGORITHM)
            
            logger.info("Admin token created", admin_id=admin_id, expires_hours=self.TOKEN_EXPIRE_HOURS)
            return token
            
        except Exception as e:
            logger.error("Failed to create admin token", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create authentication token"
            )
    
    def verify_admin_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM])
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return None
            
            # Verify it's an admin token
            if payload.get("role") != "admin":
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Admin token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid admin token", error=str(e))
            return None
        except Exception as e:
            logger.error("Token verification error", error=str(e))
            return None
    
    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request (cookie or Authorization header)"""
        try:
            # First try to get token from HTTP-only cookie
            token = request.cookies.get("admin_token")
            if token:
                return token
            
            # Fallback to Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                return auth_header[7:]
            
            return None
            
        except Exception as e:
            logger.warning("Failed to extract token from request", error=str(e))
            return None
    
    def require_admin_auth(self, request: Request) -> Dict[str, Any]:
        """Middleware function to require admin authentication"""
        token = self.extract_token_from_request(request)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        payload = self.verify_admin_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired admin token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return payload

# Security scheme for FastAPI docs
security = HTTPBearer(auto_error=False)

# Global admin auth instance
admin_auth = AdminAuth()

def require_admin(request: Request) -> Dict[str, Any]:
    """Dependency function for admin routes"""
    return admin_auth.require_admin_auth(request)