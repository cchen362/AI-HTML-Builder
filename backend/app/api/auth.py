from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth_middleware import get_current_user, require_admin

router = APIRouter()


# --- Request models ---


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=100)
    invite_code: str = Field(..., min_length=1)


class SetupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=100)


# --- Cookie helpers ---


def _set_auth_cookie(response: Response, token: str) -> None:
    from app.config import settings

    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=not settings.dev_mode,
        samesite="lax",
        max_age=30 * 24 * 3600,  # 30 days
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key="auth_token", path="/")


# --- Public auth endpoints (no auth required) ---


@router.get("/api/auth/needs-setup")
async def needs_setup():
    from app.services.auth_service import auth_service

    result = await auth_service.needs_setup()
    return {"needs_setup": result}


@router.post("/api/auth/setup")
async def setup(body: SetupRequest, response: Response):
    from app.services.auth_service import auth_service

    try:
        user = await auth_service.setup_admin(
            body.username, body.password, body.display_name
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Auto-login the admin
    _, token = await auth_service.login(body.username, body.password)
    _set_auth_cookie(response, token)
    return {"user": user}


@router.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    from app.services.auth_service import auth_service

    try:
        user, token = await auth_service.login(body.username, body.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    _set_auth_cookie(response, token)
    return {"user": user}


@router.post("/api/auth/register")
async def register(body: RegisterRequest, response: Response):
    from app.services.auth_service import auth_service

    try:
        user, token = await auth_service.register(
            body.username, body.password, body.display_name, body.invite_code
        )
    except ValueError as e:
        msg = str(e)
        if "invite" in msg.lower():
            raise HTTPException(status_code=400, detail=msg)
        if "taken" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    _set_auth_cookie(response, token)
    return {"user": user}


# --- Authenticated endpoints ---


@router.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    from app.services.auth_service import auth_service

    token = request.cookies.get("auth_token")
    if token:
        await auth_service.logout(token)
    _clear_auth_cookie(response)
    return {"success": True}


# --- Admin endpoints ---


@router.get("/api/admin/users")
async def list_users(user: dict = Depends(require_admin)):
    from app.services.auth_service import auth_service

    users = await auth_service.list_users()
    return {"users": users}


@router.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_admin)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    from app.services.auth_service import auth_service

    success = await auth_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True}


@router.get("/api/admin/invite-code")
async def get_invite_code(user: dict = Depends(require_admin)):
    from app.services.auth_service import auth_service

    code = await auth_service.get_invite_code()
    return {"invite_code": code}


@router.post("/api/admin/invite-code")
async def regenerate_invite_code(user: dict = Depends(require_admin)):
    from app.services.auth_service import auth_service

    code = await auth_service.regenerate_invite_code()
    return {"invite_code": code}
