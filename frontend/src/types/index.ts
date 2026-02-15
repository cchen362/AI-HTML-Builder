// === v2 Types (matching backend Plans 001-003) ===

/** Authenticated user from GET /api/auth/me */
export interface User {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
}

/** Chat message from GET /api/sessions/{sid}/chat */
export interface ChatMessage {
  id: number;
  session_id: string;
  document_id: string | null;
  role: 'user' | 'assistant';
  content: string;
  message_type: string;
  created_at: string;
  templateName?: string;
  userContent?: string;
}

/** Document from GET /api/sessions/{sid}/documents */
export interface Document {
  id: string;
  session_id: string;
  title: string;
  is_active: boolean;
  created_at: string;
}

/** Version from GET /api/sessions/{sid}/documents/{docId}/versions */
export interface Version {
  version: number;
  user_prompt: string;
  edit_summary: string;
  model_used: string;
  tokens_used: number;
  created_at: string;
}

/** Full version detail from GET /api/sessions/{sid}/documents/{docId}/versions/{ver} */
export interface VersionDetail extends Version {
  id: number;
  document_id: string;
  html_content: string;
}

/** Session from GET /api/sessions/{sid} */
export interface Session {
  session_id: string;
  documents: Document[];
  active_document: Document | null;
}

/** SSE event from POST /api/chat/{sid} stream */
export interface SSEEvent {
  type: 'status' | 'chunk' | 'html' | 'summary' | 'error' | 'done';
  content?: string;
  version?: number;
}


