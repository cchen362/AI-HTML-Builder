"""Brand profile management endpoints.

Brand profiles are admin-managed in auth.db. Any logged-in user can list
available brands; only admins can create or delete them.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth_middleware import get_current_user, require_admin

router = APIRouter()

_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")
_DEFAULT_ACCENT = "#64748B"


class CreateBrandRequest(BaseModel):
    name: str
    spec_text: str


@router.get("/api/brands")
async def list_brands(user: dict = Depends(get_current_user)):
    """List all brand profiles (id, name, accent_color only)."""
    from app.auth_database import get_auth_db

    db = await get_auth_db()
    cursor = await db.execute(
        "SELECT id, name, accent_color FROM brand_profiles ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    return {"brands": [dict(row) for row in rows]}


@router.post("/api/brands", status_code=201)
async def create_brand(
    body: CreateBrandRequest, user: dict = Depends(require_admin)
):
    """Create a new brand profile (admin only)."""
    from app.auth_database import get_auth_db

    name = body.name.strip()
    spec_text = body.spec_text.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Brand name is required")
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="Brand name must be 50 characters or fewer")
    if not spec_text:
        raise HTTPException(status_code=400, detail="Brand spec is required")
    if len(spec_text) > 5000:
        raise HTTPException(status_code=400, detail="Brand spec must be 5000 characters or fewer")

    # Auto-extract accent color from first hex in spec
    match = _HEX_COLOR_RE.search(spec_text)
    accent_color = match.group(0) if match else _DEFAULT_ACCENT

    brand_id = uuid.uuid4().hex[:12]
    db = await get_auth_db()
    await db.execute(
        "INSERT INTO brand_profiles (id, name, accent_color, spec_text) VALUES (?, ?, ?, ?)",
        (brand_id, name, accent_color, spec_text),
    )
    await db.commit()

    return {"id": brand_id, "name": name, "accent_color": accent_color}


@router.delete("/api/brands/{brand_id}")
async def delete_brand(brand_id: str, user: dict = Depends(require_admin)):
    """Delete a brand profile (admin only)."""
    from app.auth_database import get_auth_db

    db = await get_auth_db()
    cursor = await db.execute(
        "SELECT id FROM brand_profiles WHERE id = ?", (brand_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Brand not found")

    await db.execute("DELETE FROM brand_profiles WHERE id = ?", (brand_id,))
    await db.commit()

    return {"deleted": True}
