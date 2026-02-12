from fastapi import APIRouter, HTTPException
from app.services.session_service import session_service

router = APIRouter()


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


@router.get("/api/documents/{document_id}/versions")
async def get_versions(document_id: str):
    versions = await session_service.get_version_history(document_id)
    return {"versions": versions}


@router.get("/api/documents/{document_id}/versions/{version}")
async def get_version(document_id: str, version: int):
    ver = await session_service.get_version(document_id, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


@router.get("/api/documents/{document_id}/html")
async def get_latest_html(document_id: str):
    html = await session_service.get_latest_html(document_id)
    return {"html": html}


@router.get("/api/sessions/{session_id}/chat")
async def get_chat_history(session_id: str):
    messages = await session_service.get_chat_history(session_id)
    return {"messages": messages}
