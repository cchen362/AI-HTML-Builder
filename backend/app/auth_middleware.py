from fastapi import Depends, HTTPException, Request


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency. Reads 'auth_token' cookie, validates, returns user dict.
    Raises HTTPException(401) if missing, invalid, or expired."""
    from app.services.auth_service import auth_service

    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await auth_service.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency. Requires user to be admin. Raises HTTPException(403)."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
