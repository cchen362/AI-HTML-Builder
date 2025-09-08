"""
Admin Authentication Endpoints

Handles login/logout for admin dashboard access.
"""

from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from pydantic import BaseModel
import structlog
from ...middleware.auth import admin_auth, require_admin
from ...models.schemas import BaseResponse

logger = structlog.get_logger()

router = APIRouter()

class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str = ""
    expires_in_hours: int = 0

class AuthStatusResponse(BaseModel):
    authenticated: bool
    admin_id: str = ""
    expires_at: str = ""

@router.post("/login", response_model=LoginResponse)
async def admin_login(login_data: LoginRequest, response: Response):
    """Admin login endpoint"""
    try:
        # Verify password
        if not admin_auth.verify_admin_password(login_data.password):
            logger.warning("Failed admin login attempt")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin password"
            )
        
        # Create JWT token
        token = admin_auth.create_admin_token()
        
        # Set HTTP-only cookie (secure in production)
        response.set_cookie(
            key="admin_token",
            value=token,
            max_age=admin_auth.TOKEN_EXPIRE_HOURS * 3600,  # 8 hours in seconds
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info("Admin login successful")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            token=token,  # Also return token for client storage if needed
            expires_in_hours=admin_auth.TOKEN_EXPIRE_HOURS
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Admin login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.post("/logout", response_model=BaseResponse)
async def admin_logout(response: Response):
    """Admin logout endpoint"""
    try:
        # Clear authentication cookie
        response.delete_cookie(key="admin_token")
        
        logger.info("Admin logout successful")
        
        return BaseResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error("Admin logout error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(request: Request):
    """Check authentication status"""
    try:
        token = admin_auth.extract_token_from_request(request)
        
        if not token:
            return AuthStatusResponse(authenticated=False)
        
        payload = admin_auth.verify_admin_token(token)
        if not payload:
            return AuthStatusResponse(authenticated=False)
        
        from datetime import datetime
        expires_at = datetime.fromtimestamp(payload.get("exp", 0)).isoformat()
        
        return AuthStatusResponse(
            authenticated=True,
            admin_id=payload.get("sub", "admin"),
            expires_at=expires_at
        )
        
    except Exception as e:
        logger.error("Auth status check error", error=str(e))
        return AuthStatusResponse(authenticated=False)

@router.get("/verify")
async def verify_admin_auth(admin_data: dict = Depends(require_admin)):
    """Protected endpoint to verify admin authentication"""
    return {
        "authenticated": True,
        "admin_id": admin_data.get("sub"),
        "role": admin_data.get("role"),
        "message": "Admin authentication verified"
    }