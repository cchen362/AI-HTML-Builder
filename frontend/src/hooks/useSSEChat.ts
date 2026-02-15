import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '../services/api';
import type { ChatMessage, Document, SSEEvent } from '../types';

interface UseSSEChatOptions {
  onHtmlUpdate?: (html: string, version?: number) => void;
  onError?: (error: string) => void;
}

interface UseSSEChatReturn {
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  currentStatus: string;
  streamingContent: string;
  currentHtml: string;
  activeDocument: Document | null;
  documents: Document[];
  isInitializing: boolean;
  sendMessage: (content: string, documentId?: string, templateName?: string, userContent?: string) => Promise<void>;
  cancelRequest: () => void;
  switchDocument: (docId: string) => Promise<void>;
  refreshDocuments: () => Promise<void>;
  startNewSession: () => Promise<void>;
}

const SESSION_KEY = 'ai-html-builder-session-id';

export function useSSEChat(options: UseSSEChatOptions = {}): UseSSEChatReturn {
  const { onHtmlUpdate, onError } = options;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStatus, setCurrentStatus] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [currentHtml, setCurrentHtml] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocument, setActiveDocument] = useState<Document | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  const abortRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const sendingRef = useRef(false);

  // Keep ref in sync for use in callbacks
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Initialize session on mount
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        // Check sessionStorage for existing session
        const stored = sessionStorage.getItem(SESSION_KEY);
        let sid = stored;

        if (sid) {
          // Validate the stored session still exists
          try {
            const session = await api.getSession(sid);
            if (!cancelled) {
              setDocuments(session.documents);
              setActiveDocument(session.active_document);

              // Load current HTML if there's an active document
              if (session.active_document) {
                const { html } = await api.getDocumentHtml(session.active_document.id);
                if (!cancelled) setCurrentHtml(html);
              }
            }
          } catch {
            // Session doesn't exist or is invalid, create new one
            sid = null;
          }
        }

        if (!sid) {
          const { session_id } = await api.createSession();
          sid = session_id;
          sessionStorage.setItem(SESSION_KEY, sid);
        }

        if (!cancelled) {
          setSessionId(sid);

          // Load chat history
          try {
            const { messages: history } = await api.getChatHistory(sid);
            if (!cancelled) setMessages(history);
          } catch {
            // No history yet, that's fine
          }
        }
      } catch (err) {
        if (!cancelled && onError) {
          onError(err instanceof Error ? err.message : 'Failed to initialize session');
        }
      } finally {
        if (!cancelled) setIsInitializing(false);
      }
    }

    init();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshDocuments = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;

    try {
      const session = await api.getSession(sid);
      setDocuments(session.documents);
      setActiveDocument(session.active_document);

      // Load HTML for active document
      if (session.active_document) {
        const { html } = await api.getDocumentHtml(session.active_document.id);
        setCurrentHtml(html);
        onHtmlUpdate?.(html);
      }
    } catch {
      // silently ignore refresh failures
    }
  }, [onHtmlUpdate]);

  const switchDocument = useCallback(async (docId: string) => {
    const sid = sessionIdRef.current;
    if (!sid) return;

    try {
      await api.switchDocument(sid, docId);
      const { html } = await api.getDocumentHtml(docId);
      setCurrentHtml(html);
      onHtmlUpdate?.(html);

      // Update active document in local state
      setDocuments(prev => prev.map(d => ({ ...d, is_active: d.id === docId })));
      setActiveDocument(prev => {
        const doc = documents.find(d => d.id === docId);
        return doc ? { ...doc, is_active: true } : prev;
      });
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'Failed to switch document');
    }
  }, [documents, onHtmlUpdate, onError]);

  const sendMessage = useCallback(async (content: string, documentId?: string, templateName?: string, userContent?: string) => {
    const sid = sessionIdRef.current;
    if (!sid || !content.trim() || sendingRef.current) return;
    sendingRef.current = true;

    // Add optimistic user message
    const userMsg: ChatMessage = {
      id: Date.now(),
      session_id: sid,
      document_id: documentId ?? null,
      role: 'user',
      content: content.trim(),
      message_type: 'text',
      created_at: new Date().toISOString(),
      ...(templateName && { templateName, userContent: userContent || content.trim() }),
    };
    setMessages(prev => [...prev, userMsg]);

    // Start streaming
    const controller = new AbortController();
    abortRef.current = controller;
    setIsStreaming(true);
    setCurrentStatus('Connecting...');
    setStreamingContent('');

    try {
      const response = await api.sendChatMessage(sid, content, documentId, controller.signal, templateName, userContent);

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedChunks = '';
      let assistantSummary = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double newlines (SSE event boundary)
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed) continue;

          // Extract the data line (format: "data: {...}")
          let dataStr = '';
          for (const line of trimmed.split('\n')) {
            if (line.startsWith('data:')) {
              dataStr = line.slice(5).trim();
            }
          }

          if (!dataStr) continue;

          let event: SSEEvent;
          try {
            event = JSON.parse(dataStr) as SSEEvent;
          } catch {
            continue;
          }

          switch (event.type) {
            case 'status':
              setCurrentStatus(event.content || '');
              break;

            case 'chunk':
              accumulatedChunks += event.content || '';
              setStreamingContent(accumulatedChunks);
              break;

            case 'html':
              if (event.content) {
                setCurrentHtml(event.content);
                onHtmlUpdate?.(event.content, event.version);
              }
              break;

            case 'summary':
              assistantSummary = event.content || '';
              break;

            case 'error':
              onError?.(event.content || 'Unknown error');
              setCurrentStatus('');
              break;

            case 'done': {
              // Add assistant message to history
              if (assistantSummary.trim()) {
                const assistantMsg: ChatMessage = {
                  id: Date.now() + 1,
                  session_id: sid,
                  document_id: documentId ?? null,
                  role: 'assistant',
                  content: assistantSummary.trim(),
                  message_type: 'text',
                  created_at: new Date().toISOString(),
                };
                setMessages(prev => [...prev, assistantMsg]);
              }

              setCurrentStatus('');
              setStreamingContent('');

              // Refresh documents (a new doc may have been created)
              await refreshDocuments();
              break;
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setCurrentStatus('Cancelled');
      } else {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        onError?.(msg);
        setCurrentStatus('');
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      sendingRef.current = false;
    }
  }, [onHtmlUpdate, onError, refreshDocuments]);

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const startNewSession = useCallback(async () => {
    sessionStorage.removeItem(SESSION_KEY);
    setMessages([]);
    setDocuments([]);
    setActiveDocument(null);
    setCurrentHtml('');
    setStreamingContent('');
    setCurrentStatus('');
    setIsStreaming(false);

    try {
      const { session_id } = await api.createSession();
      sessionStorage.setItem(SESSION_KEY, session_id);
      setSessionId(session_id);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'Failed to create new session');
    }
  }, [onError]);

  return {
    sessionId,
    messages,
    isStreaming,
    currentStatus,
    streamingContent,
    currentHtml,
    activeDocument,
    documents,
    isInitializing,
    sendMessage,
    cancelRequest,
    switchDocument,
    refreshDocuments,
    startNewSession,
  };
}
