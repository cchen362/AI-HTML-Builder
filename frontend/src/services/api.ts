import type { Session, Version, VersionDetail, ChatMessage, User, SessionSummary } from '../types';

const BASE = '';

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...init,
    credentials: 'same-origin',
  });
  if (res.status === 401) {
    window.dispatchEvent(new Event('auth:unauthorized'));
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

let _sessionId: string | null = null;

export function setSessionId(sid: string | null): void {
  _sessionId = sid;
}

function getSessionId(): string {
  if (!_sessionId) throw new Error('No active session');
  return _sessionId;
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

  /** Switch the active document in a session. */
  switchDocument(sessionId: string, docId: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}/documents/${docId}/switch`, {
      method: 'POST',
    });
  },

  /** Get the latest HTML content for a document. */
  getDocumentHtml(docId: string): Promise<{ html: string }> {
    return json(`/api/sessions/${getSessionId()}/documents/${docId}/html`);
  },

  /** Get version history for a document. */
  getVersions(docId: string): Promise<{ versions: Version[] }> {
    return json(`/api/sessions/${getSessionId()}/documents/${docId}/versions`);
  },

  /** Get a specific version with full HTML content. */
  getVersion(docId: string, version: number): Promise<VersionDetail> {
    return json(`/api/sessions/${getSessionId()}/documents/${docId}/versions/${version}`);
  },

  /** Get chat history for a session. */
  async getChatHistory(sessionId: string): Promise<{ messages: ChatMessage[] }> {
    const raw = await json<{ messages: Record<string, unknown>[] }>(`/api/sessions/${sessionId}/chat`);
    return {
      messages: raw.messages.map((m) => ({
        ...m,
        // Map snake_case DB columns to camelCase frontend fields
        templateName: (m.template_name as string | null) ?? undefined,
        userContent: (m.user_content as string | null) ?? undefined,
      })) as ChatMessage[],
    };
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
    templateName?: string,
    userContent?: string,
  ): Promise<Response> {
    const body: Record<string, string> = { message };
    if (documentId) {
      body.document_id = documentId;
    }
    if (templateName) {
      body.template_name = templateName;
    }
    if (userContent) {
      body.user_content = userContent;
    }

    const res = await fetch(`${BASE}/api/chat/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal,
      credentials: 'same-origin',
    });

    if (res.status === 401) {
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw new Error('Unauthorized');
    }

    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`);
    }

    return res;
  },

  /** Restore a historical version (creates a new version from old HTML). */
  restoreVersion(docId: string, version: number): Promise<{ version: number }> {
    return json(`/api/sessions/${getSessionId()}/documents/${docId}/versions/${version}/restore`, {
      method: 'POST',
    });
  },

  /** Rename a document. */
  renameDocument(docId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${getSessionId()}/documents/${docId}`, {
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
    return json(`/api/sessions/${getSessionId()}/documents/${documentId}/manual-edit`, {
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
      `${BASE}/api/sessions/${getSessionId()}/documents/${documentId}/export/${format}?${params.toString()}`,
      { method: 'POST', credentials: 'same-origin' },
    );

    if (res.status === 401) {
      window.dispatchEvent(new Event('auth:unauthorized'));
      throw new Error('Unauthorized');
    }

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

  /** List all sessions for the current user. */
  listSessions(limit?: number, offset?: number): Promise<{ sessions: SessionSummary[] }> {
    const params = new URLSearchParams();
    if (limit !== undefined) params.set('limit', String(limit));
    if (offset !== undefined) params.set('offset', String(offset));
    const qs = params.toString();
    return json(`/api/sessions${qs ? '?' + qs : ''}`);
  },

  /** Delete a session. */
  deleteSession(sessionId: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}`, { method: 'DELETE' });
  },

  /** Update session title. */
  updateSessionTitle(sessionId: string, title: string): Promise<{ success: boolean }> {
    return json(`/api/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  },
};

// === Auth API ===

export const authApi = {
  needsSetup(): Promise<{ needs_setup: boolean }> {
    return json('/api/auth/needs-setup');
  },

  setup(username: string, password: string, displayName: string): Promise<{ user: User }> {
    return json('/api/auth/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, display_name: displayName }),
    });
  },

  login(username: string, password: string): Promise<{ user: User }> {
    return json('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  },

  register(username: string, password: string, displayName: string, inviteCode: string): Promise<{ user: User }> {
    return json('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, display_name: displayName, invite_code: inviteCode }),
    });
  },

  getMe(): Promise<{ user: User }> {
    return json('/api/auth/me');
  },

  logout(): Promise<{ success: boolean }> {
    return json('/api/auth/logout', { method: 'POST' });
  },
};

// === Admin API ===

export const adminApi = {
  getUsers(): Promise<{ users: User[] }> {
    return json('/api/admin/users');
  },

  deleteUser(userId: string): Promise<{ success: boolean }> {
    return json(`/api/admin/users/${userId}`, { method: 'DELETE' });
  },

  getInviteCode(): Promise<{ invite_code: string }> {
    return json('/api/admin/invite-code');
  },

  regenerateInviteCode(): Promise<{ invite_code: string }> {
    return json('/api/admin/invite-code', { method: 'POST' });
  },
};
