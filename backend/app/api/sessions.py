from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.session_service import session_service

router = APIRouter()


async def _require_document_ownership(
    document_id: str, session_id: str
) -> None:
    """Raise 403 if the document doesn't belong to the session."""
    owns = await session_service.verify_document_ownership(
        document_id, session_id
    )
    if not owns:
        raise HTTPException(
            status_code=403,
            detail="Document does not belong to this session",
        )


@router.post("/api/sessions")
async def create_session():
    session_id = await session_service.create_session()
    return {"session_id": session_id}


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    docs = await session_service.get_session_documents(session_id)
    active = await session_service.get_active_document(session_id)
    return {
        "session_id": session_id,
        "documents": docs,
        "active_document": active,
    }


@router.get("/api/sessions/{session_id}/documents")
async def get_documents(session_id: str):
    docs = await session_service.get_session_documents(session_id)
    return {"documents": docs}


@router.post("/api/sessions/{session_id}/documents/{document_id}/switch")
async def switch_document(session_id: str, document_id: str):
    success = await session_service.switch_document(session_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found in session")
    return {"success": success}


@router.get("/api/sessions/{session_id}/documents/{document_id}/versions")
async def get_versions(session_id: str, document_id: str):
    await _require_document_ownership(document_id, session_id)
    versions = await session_service.get_version_history(document_id)
    return {"versions": versions}


@router.get("/api/sessions/{session_id}/documents/{document_id}/versions/{version}")
async def get_version(session_id: str, document_id: str, version: int):
    await _require_document_ownership(document_id, session_id)
    ver = await session_service.get_version(document_id, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


@router.get("/api/sessions/{session_id}/documents/{document_id}/html")
async def get_latest_html(session_id: str, document_id: str):
    await _require_document_ownership(document_id, session_id)
    html = await session_service.get_latest_html(document_id)
    return {"html": html}


@router.post("/api/sessions/{session_id}/documents/{document_id}/versions/{version}/restore")
async def restore_version(session_id: str, document_id: str, version: int):
    await _require_document_ownership(document_id, session_id)
    try:
        new_version = await session_service.restore_version(document_id, version)
        return {"version": new_version}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/sessions/{session_id}/chat")
async def get_chat_history(session_id: str):
    messages = await session_service.get_chat_history(session_id)
    return {"messages": messages}


class FromTemplateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    html_content: str = Field(..., min_length=1)


@router.post("/api/sessions/{session_id}/documents/from-template")
async def create_from_template(session_id: str, body: FromTemplateRequest):
    """Create a new document pre-populated with template HTML."""
    doc_id = await session_service.create_document(session_id, title=body.title)
    version = await session_service.save_version(
        document_id=doc_id,
        html_content=body.html_content,
        user_prompt="Created from template",
        edit_summary=f"Template: {body.title}",
        model_used="template",
        tokens_used=0,
    )
    return {"document_id": doc_id, "version": version}


class ManualEditRequest(BaseModel):
    html_content: str = Field(..., min_length=1)


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.patch("/api/sessions/{session_id}/documents/{document_id}")
async def rename_document(session_id: str, document_id: str, body: RenameRequest):
    await _require_document_ownership(document_id, session_id)
    success = await session_service.rename_document(document_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}


@router.delete("/api/sessions/{session_id}/documents/{document_id}")
async def delete_document(session_id: str, document_id: str):
    success = await session_service.delete_document(session_id, document_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document (not found or last remaining document)",
        )
    return {"success": True}


@router.post("/api/sessions/{session_id}/documents/{document_id}/manual-edit")
async def save_manual_edit(session_id: str, document_id: str, body: ManualEditRequest):
    """Save manual HTML edits as a new version."""
    await _require_document_ownership(document_id, session_id)
    version = await session_service.save_manual_edit(
        document_id, body.html_content
    )
    return {"version": version, "success": True}
