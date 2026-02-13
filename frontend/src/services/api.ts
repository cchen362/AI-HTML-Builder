import type { Session, Document, Version, VersionDetail, ChatMessage } from '../types';

const BASE = '';

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Create a new session. Returns {session_id}. */
  createSession(): Promise<{ session_id: string }> {
    return json('/api/sessions', { method: 'POST' });
  },

  /** Get session info with documents and active document. */
  getSession(sessionId: string): Promise<Session> {
    return json(`/api/sessions/${sessionId}`);
  },

  /** List all documents in a session. */
  getDocuments(sessionId: string): Promise<{ documents: Document[] }> {
    return json(`/api/sessions/${sessionId}/documents`);
  },

  /** Switch the active document in a session. */
  switchDocument(sessionId: string, docId: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}/documents/${docId}/switch`, {
      method: 'POST',
    });
  },

  /** Get the latest HTML content for a document. */
  getDocumentHtml(docId: string): Promise<{ html: string }> {
    return json(`/api/documents/${docId}/html`);
  },

  /** Get version history for a document. */
  getVersions(docId: string): Promise<{ versions: Version[] }> {
    return json(`/api/documents/${docId}/versions`);
  },

  /** Get a specific version with full HTML content. */
  getVersion(docId: string, version: number): Promise<VersionDetail> {
    return json(`/api/documents/${docId}/versions/${version}`);
  },

  /** Get chat history for a session. */
  getChatHistory(sessionId: string): Promise<{ messages: ChatMessage[] }> {
    return json(`/api/sessions/${sessionId}/chat`);
  },

  /**
   * Send a chat message and get back the raw Response for SSE streaming.
   * The caller must process the ReadableStream.
   */
  async sendChatMessage(
    sessionId: string,
    message: string,
    documentId?: string,
    signal?: AbortSignal,
  ): Promise<Response> {
    const body: { message: string; document_id?: string } = { message };
    if (documentId) {
      body.document_id = documentId;
    }

    const res = await fetch(`${BASE}/api/chat/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal,
    });

    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`);
    }

    return res;
  },

  /** Create a new document from a custom template's HTML. */
  createFromTemplate(
    sessionId: string,
    title: string,
    htmlContent: string,
  ): Promise<{ document_id: string; version: number }> {
    return json(`/api/sessions/${sessionId}/documents/from-template`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, html_content: htmlContent }),
    });
  },

  /** Restore a historical version (creates a new version from old HTML). */
  restoreVersion(docId: string, version: number): Promise<{ version: number }> {
    return json(`/api/documents/${docId}/versions/${version}/restore`, {
      method: 'POST',
    });
  },

  /** Rename a document. */
  renameDocument(docId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/documents/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  },

  /** Delete a document from a session. */
  deleteDocument(sessionId: string, docId: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}/documents/${docId}`, {
      method: 'DELETE',
    });
  },

  /** Save manual HTML edits as a new version. */
  saveManualEdit(documentId: string, htmlContent: string): Promise<{ version: number; success: boolean }> {
    return json(`/api/documents/${documentId}/manual-edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html_content: htmlContent }),
    });
  },

  /** Download a document export in the specified format. */
  async exportDocument(
    documentId: string,
    format: 'html' | 'pptx' | 'pdf' | 'png',
    title?: string,
  ): Promise<void> {
    const params = new URLSearchParams();
    if (title) params.set('title', title);

    const res = await fetch(
      `${BASE}/api/export/${documentId}/${format}?${params.toString()}`,
      { method: 'POST' },
    );

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      throw new Error(errorData?.detail || `Export failed: ${res.status}`);
    }

    // Extract filename from Content-Disposition header
    const disposition = res.headers.get('Content-Disposition');
    const filenameMatch = disposition?.match(/filename="(.+)"/);
    const filename = filenameMatch?.[1] || `export.${format}`;

    // Download the blob
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
