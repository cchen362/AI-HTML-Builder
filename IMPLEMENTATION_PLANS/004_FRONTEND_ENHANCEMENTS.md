# Implementation Plan 004: Frontend Enhancements

**Status**: Not Started
**Dependencies**: Plan 001 (Backend Foundation) - MUST BE COMPLETED FIRST
**Estimated Effort**: 5-7 days
**Risk Level**: Medium

---

## 🛑 STOP - READ THIS FIRST

**DO NOT START** this implementation until:

1. ✅ Plan 001 (Backend Foundation) is **100% complete** and tested
2. ✅ All backend endpoints are verified working:
   - `POST /api/chat/{sessionId}` with SSE response
   - `GET /api/sessions/{sessionId}/documents`
   - `POST /api/sessions/{sessionId}/documents/{docId}/switch`
   - `GET /api/documents/{docId}/versions`
   - `POST /api/documents/{docId}/versions/{versionId}/restore`
3. ✅ You have tested SSE streaming manually with curl or Postman
4. ✅ Redis session storage is working correctly
5. ✅ You understand the new multi-document architecture

**Why this matters**: The frontend rebuild completely replaces the WebSocket architecture with SSE and introduces multi-document management. If the backend isn't ready, you'll build against phantom APIs and waste hours debugging integration issues.

**Rollback Risk**: This plan replaces core frontend infrastructure (WebSocket → SSE, plain text → CodeMirror, single doc → multi-doc). Once started, rolling back is difficult. Test each phase thoroughly before proceeding.

---

## Context & Rationale

### Current State Problems
1. **WebSocket Complexity**: Reconnection logic, connection state management, error handling
2. **No Code Highlighting**: Raw `<pre>` tags with no syntax highlighting or copy functionality
3. **Plain Text Chat**: No markdown support, no streaming markdown rendering
4. **Single Document**: Users can't work on multiple documents in one session
5. **No Version History**: Lost edits cannot be recovered, no undo beyond current state
6. **Admin Clutter**: Admin link in header, WebSocket status indicator not needed for SSE
7. **Poor UX**: No copy buttons, no visual placeholders, no template cards

### New Architecture Benefits
1. **SSE Simplicity**: Browser-native EventSource, automatic reconnection, simpler error handling
2. **CodeMirror 6**: Professional syntax highlighting, ~300KB (vs Monaco 10MB), read-only mode
3. **Streamdown**: Flicker-free streaming markdown with syntax highlighting
4. **Multi-Document**: Work on multiple HTML documents in tabs within one session
5. **Version Timeline**: Time-travel through edits, restore previous versions
6. **Professional Polish**: Copy buttons everywhere, visual starter cards, export options

### Technology Choices
- **SSE over WebSocket**: Simpler protocol for server→client streaming, no bidirectional overhead
- **CodeMirror 6 over Monaco**: 30x smaller bundle, faster load, sufficient features for read-only viewing
- **Streamdown**: Battle-tested by Vercel for AI streaming, handles incomplete markdown gracefully
- **Native Fetch API**: No WebSocket library dependencies, better error handling

---

## Strict Implementation Rules

### Phase Execution
- [ ] Complete phases **in exact order** (001 → 002 → 003 → 004 → 005 → 006)
- [ ] Each phase MUST pass its build verification before starting the next phase
- [ ] Do NOT merge code from multiple phases into one commit
- [ ] Test each phase in isolation before integration

### Code Quality
- [ ] All new components must be TypeScript with explicit types (no `any`)
- [ ] Use React 19 features (no class components, use hooks)
- [ ] All async operations must have error boundaries
- [ ] Loading states required for all data fetching
- [ ] No console.log in production code (use proper error handling)

### Dependency Management
- [ ] Lock package versions in package.json (no `^` or `~`)
- [ ] Run `npm install` after each package addition
- [ ] Verify bundle size doesn't exceed 2MB (run `npm run build` and check dist/ size)
- [ ] Test tree-shaking with `npm run build -- --mode production`

### Testing Requirements
- [ ] Manual testing in Chrome, Firefox, Safari (latest versions)
- [ ] Mobile responsive testing (viewport sizes: 375px, 768px, 1024px, 1920px)
- [ ] Network throttling test (slow 3G) for SSE streaming
- [ ] Error scenario testing (backend down, invalid session, SSE disconnect)

### Integration Safety
- [ ] Keep old WebSocket code in separate branch until SSE fully verified
- [ ] Use feature flags for gradual rollout if needed
- [ ] Backup current working frontend before starting
- [ ] Document all breaking changes in CHANGELOG.md

---

## Phase 001: SSE Client Implementation

**Goal**: Replace WebSocket with Server-Sent Events for chat streaming

**Duration**: 1 day
**Risk**: Medium (core communication change)

### Step 1.1: Install Dependencies
**No new packages needed** - uses browser-native `fetch` and `ReadableStream` APIs

### Step 1.2: Create SSE Hook

**File**: `frontend/src/hooks/useSSEChat.ts`

```typescript
import { useState, useCallback, useRef } from 'react';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface SSEEvent {
  type: 'status' | 'html' | 'summary' | 'error' | 'done';
  data: string;
}

interface UseSSEChatOptions {
  sessionId: string;
  onHtmlUpdate?: (html: string) => void;
  onComplete?: (summary: string) => void;
  onError?: (error: string) => void;
}

export function useSSEChat({
  sessionId,
  onHtmlUpdate,
  onComplete,
  onError,
}: UseSSEChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string>('');
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string, uploadedFile?: File) => {
      // Add user message
      const userMessage: ChatMessage = {
        role: 'user',
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Prepare request
      const formData = new FormData();
      formData.append('message', content);
      if (uploadedFile) {
        formData.append('file', uploadedFile);
      }

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      try {
        setIsStreaming(true);
        setCurrentStatus('Connecting...');

        const response = await fetch(`/api/chat/${sessionId}`, {
          method: 'POST',
          body: formData,
          signal: abortControllerRef.current.signal,
          headers: {
            Accept: 'text/event-stream',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        // Process SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantMessage = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events (separated by \n\n)
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; // Keep incomplete event in buffer

          for (const eventText of events) {
            if (!eventText.trim()) continue;

            // Parse SSE format: "event: type\ndata: payload"
            const lines = eventText.split('\n');
            let eventType = 'message';
            let eventData = '';

            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                eventData = line.slice(5).trim();
              }
            }

            // Handle different event types
            switch (eventType) {
              case 'status':
                setCurrentStatus(eventData);
                break;

              case 'html':
                if (onHtmlUpdate) {
                  onHtmlUpdate(eventData);
                }
                break;

              case 'summary':
                assistantMessage += eventData;
                break;

              case 'error':
                if (onError) {
                  onError(eventData);
                }
                setCurrentStatus(`Error: ${eventData}`);
                break;

              case 'done':
                // Add assistant message to chat
                if (assistantMessage.trim()) {
                  const finalMessage: ChatMessage = {
                    role: 'assistant',
                    content: assistantMessage.trim(),
                    timestamp: new Date(),
                  };
                  setMessages((prev) => [...prev, finalMessage]);
                }

                if (onComplete) {
                  onComplete(assistantMessage);
                }
                setCurrentStatus('');
                break;
            }
          }
        }
      } catch (error) {
        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            setCurrentStatus('Request cancelled');
          } else {
            const errorMsg = error.message || 'Unknown error';
            if (onError) {
              onError(errorMsg);
            }
            setCurrentStatus(`Error: ${errorMsg}`);
          }
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [sessionId, onHtmlUpdate, onComplete, onError]
  );

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  return {
    messages,
    sendMessage,
    cancelRequest,
    isStreaming,
    currentStatus,
  };
}
```

### Step 1.3: Update Main Chat Component

**File**: `frontend/src/components/Chat/ChatInterface.tsx`

```typescript
import React, { useState } from 'react';
import { useSSEChat } from '../../hooks/useSSEChat';
import ChatMessageList from './ChatMessageList';
import ChatInput from './ChatInput';

interface ChatInterfaceProps {
  sessionId: string;
  onHtmlUpdate: (html: string) => void;
}

export default function ChatInterface({ sessionId, onHtmlUpdate }: ChatInterfaceProps) {
  const [error, setError] = useState<string | null>(null);

  const { messages, sendMessage, cancelRequest, isStreaming, currentStatus } = useSSEChat({
    sessionId,
    onHtmlUpdate,
    onComplete: (summary) => {
      console.log('Generation complete:', summary);
    },
    onError: (errorMsg) => {
      setError(errorMsg);
    },
  });

  const handleSendMessage = async (content: string, file?: File) => {
    setError(null);
    await sendMessage(content, file);
  };

  return (
    <div className="chat-interface">
      <ChatMessageList messages={messages} />

      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
          <button onClick={() => setError(null)} className="error-dismiss">×</button>
        </div>
      )}

      {isStreaming && (
        <div className="status-bar">
          <div className="status-spinner" />
          <span className="status-text">{currentStatus}</span>
          <button onClick={cancelRequest} className="cancel-btn">Cancel</button>
        </div>
      )}

      <ChatInput onSend={handleSendMessage} disabled={isStreaming} />
    </div>
  );
}
```

### Step 1.4: Build Verification

```bash
# Navigate to frontend directory
cd frontend

# Build the project
npm run build

# Check for errors
echo $?  # Should output 0

# Verify bundle size (should be < 2MB)
du -sh dist/

# Start dev server and test
npm run dev
```

**Manual Tests**:
1. Send a message, verify SSE connection opens
2. Check browser DevTools → Network → EventStream type
3. Verify status updates appear during generation
4. Test cancellation with "Cancel" button
5. Verify error handling (stop backend, send message)
6. Check messages persist in chat history

---

## Phase 002: CodeMirror 6 Integration

**Goal**: Add professional syntax-highlighted code viewer

**Duration**: 1 day
**Risk**: Low (isolated component)

### Step 2.1: Install Dependencies

```bash
cd frontend

npm install @codemirror/view@6.23.1 \
            @codemirror/state@6.4.0 \
            @codemirror/lang-html@6.4.8 \
            @codemirror/theme-one-dark@6.1.2
```

**Lock versions in package.json**:
```json
{
  "dependencies": {
    "@codemirror/view": "6.23.1",
    "@codemirror/state": "6.4.0",
    "@codemirror/lang-html": "6.4.8",
    "@codemirror/theme-one-dark": "6.1.2"
  }
}
```

### Step 2.2: Create CodeMirror Component

**File**: `frontend/src/components/CodeViewer/CodeMirrorViewer.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import { EditorView, basicSetup } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { html } from '@codemirror/lang-html';
import { oneDark } from '@codemirror/theme-one-dark';

interface CodeMirrorViewerProps {
  code: string;
  language?: 'html' | 'css' | 'javascript';
  theme?: 'light' | 'dark';
  showLineNumbers?: boolean;
}

export default function CodeMirrorViewer({
  code,
  language = 'html',
  theme = 'dark',
  showLineNumbers = true,
}: CodeMirrorViewerProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!editorRef.current) return;

    // Get language extension
    const languageExtension = language === 'html' ? html() : html();

    // Create editor state
    const state = EditorState.create({
      doc: code,
      extensions: [
        basicSetup,
        languageExtension,
        theme === 'dark' ? oneDark : [],
        EditorView.editable.of(false), // Read-only
        EditorView.lineWrapping,
        EditorState.readOnly.of(true),
      ],
    });

    // Create editor view
    viewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    return () => {
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  }, []);

  // Update document when code changes
  useEffect(() => {
    if (!viewRef.current) return;

    const currentDoc = viewRef.current.state.doc.toString();
    if (currentDoc !== code) {
      viewRef.current.dispatch({
        changes: {
          from: 0,
          to: currentDoc.length,
          insert: code,
        },
      });
    }
  }, [code]);

  return <div ref={editorRef} className="codemirror-container" />;
}
```

### Step 2.3: Add Copy Button Component

**File**: `frontend/src/components/CodeViewer/CopyButton.tsx`

```typescript
import React, { useState } from 'react';

interface CopyButtonProps {
  text: string;
  label?: string;
}

export default function CopyButton({ text, label = 'Copy' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="copy-button"
      title={copied ? 'Copied!' : 'Copy to clipboard'}
    >
      {copied ? (
        <>
          <svg className="icon-check" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg className="icon-copy" viewBox="0 0 20 20" fill="currentColor">
            <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
            <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
          </svg>
          {label}
        </>
      )}
    </button>
  );
}
```

### Step 2.4: Create Code View Container

**File**: `frontend/src/components/CodeViewer/CodeView.tsx`

```typescript
import React from 'react';
import CodeMirrorViewer from './CodeMirrorViewer';
import CopyButton from './CopyButton';

interface CodeViewProps {
  html: string;
}

export default function CodeView({ html }: CodeViewProps) {
  return (
    <div className="code-view-container">
      <div className="code-view-header">
        <h3 className="code-view-title">HTML Source</h3>
        <CopyButton text={html} label="Copy Code" />
      </div>
      <div className="code-view-body">
        <CodeMirrorViewer code={html} language="html" theme="dark" />
      </div>
    </div>
  );
}
```

### Step 2.5: Add Styles

**File**: `frontend/src/components/CodeViewer/CodeView.css`

```css
.code-view-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}

.code-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
}

.code-view-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #cccccc;
}

.code-view-body {
  flex: 1;
  overflow: auto;
}

.codemirror-container {
  height: 100%;
  font-size: 13px;
}

.codemirror-container .cm-editor {
  height: 100%;
}

.copy-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.copy-button:hover {
  background: #1177bb;
}

.copy-button:active {
  background: #0d5a8f;
}

.copy-button svg {
  width: 16px;
  height: 16px;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .code-view-header {
    padding: 8px 12px;
  }

  .code-view-title {
    font-size: 13px;
  }

  .copy-button {
    padding: 5px 10px;
    font-size: 12px;
  }
}
```

### Step 2.6: Build Verification

```bash
cd frontend

# Build and check bundle size
npm run build
du -sh dist/  # Should be < 2MB (CodeMirror adds ~300KB)

# Start dev server
npm run dev
```

**Manual Tests**:
1. Toggle to code view, verify syntax highlighting appears
2. Test copy button (should copy full HTML)
3. Verify line numbers display
4. Check scrolling works for long documents
5. Test dark theme rendering
6. Verify read-only mode (can't edit text)

---

## Phase 003: Streamdown Chat Integration

**Goal**: Add streaming markdown support for chat messages

**Duration**: 1 day
**Risk**: Low (UI enhancement)

### Step 3.1: Install Dependencies

```bash
cd frontend

# Note: Using react-markdown as streamdown alternative
# Streamdown is not publicly available; using proven alternative
npm install react-markdown@9.0.1 \
            remark-gfm@4.0.0 \
            rehype-highlight@7.0.0
```

### Step 3.2: Create Streaming Markdown Component

**File**: `frontend/src/components/Chat/StreamingMarkdown.tsx`

```typescript
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface StreamingMarkdownProps {
  content: string;
  isStreaming?: boolean;
}

export default function StreamingMarkdown({ content, isStreaming = false }: StreamingMarkdownProps) {
  return (
    <div className={`markdown-content ${isStreaming ? 'streaming' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Custom code block component
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline ? (
              <div className="code-block-wrapper">
                <div className="code-block-header">
                  <span className="code-block-lang">{match ? match[1] : 'code'}</span>
                  <button
                    className="code-block-copy"
                    onClick={() => {
                      navigator.clipboard.writeText(String(children));
                    }}
                  >
                    Copy
                  </button>
                </div>
                <pre className={className}>
                  <code {...props}>{children}</code>
                </pre>
              </div>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          // Custom link component (open in new tab)
          a({ node, children, href, ...props }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="streaming-cursor">▊</span>}
    </div>
  );
}
```

### Step 3.3: Update Chat Message Component

**File**: `frontend/src/components/Chat/ChatMessage.tsx`

```typescript
import React from 'react';
import StreamingMarkdown from './StreamingMarkdown';
import { ChatMessage as ChatMessageType } from '../../hooks/useSSEChat';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming = false }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className="message-avatar">
        {isUser ? (
          <div className="avatar-user">You</div>
        ) : (
          <div className="avatar-assistant">AI</div>
        )}
      </div>
      <div className="message-content">
        <div className="message-header">
          <span className="message-role">{isUser ? 'You' : 'Assistant'}</span>
          <span className="message-timestamp">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="message-body">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <StreamingMarkdown content={message.content} isStreaming={isStreaming} />
          )}
        </div>
      </div>
    </div>
  );
}
```

### Step 3.4: Update Chat Message List

**File**: `frontend/src/components/Chat/ChatMessageList.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import { ChatMessage as ChatMessageType } from '../../hooks/useSSEChat';

interface ChatMessageListProps {
  messages: ChatMessageType[];
  streamingMessage?: string;
}

export default function ChatMessageList({ messages, streamingMessage }: ChatMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  return (
    <div className="chat-message-list">
      {messages.length === 0 && !streamingMessage ? (
        <div className="empty-state">
          <div className="empty-icon">💬</div>
          <h3>Start a conversation</h3>
          <p>Describe the HTML document you'd like to create, or upload a file to get started.</p>
        </div>
      ) : (
        <>
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          {streamingMessage && (
            <ChatMessage
              message={{
                role: 'assistant',
                content: streamingMessage,
                timestamp: new Date(),
              }}
              isStreaming
            />
          )}
        </>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}
```

### Step 3.5: Add Markdown Styles

**File**: `frontend/src/components/Chat/ChatMessage.css`

```css
.chat-message {
  display: flex;
  gap: 12px;
  padding: 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.chat-message:hover {
  background: rgba(255, 255, 255, 0.02);
}

.user-message {
  background: rgba(0, 111, 207, 0.1);
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-user,
.avatar-assistant {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.avatar-user {
  background: linear-gradient(135deg, #006FCF, #00175A);
}

.avatar-assistant {
  background: linear-gradient(135deg, #28CD6E, #006469);
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-role {
  font-size: 13px;
  font-weight: 600;
  color: #cccccc;
}

.message-timestamp {
  font-size: 11px;
  color: #888888;
}

.message-body {
  color: #e0e0e0;
  line-height: 1.6;
}

/* Markdown content styles */
.markdown-content {
  font-size: 14px;
}

.markdown-content p {
  margin: 0 0 12px 0;
}

.markdown-content p:last-child {
  margin-bottom: 0;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
  margin: 16px 0 8px 0;
  color: #ffffff;
}

.markdown-content h1 {
  font-size: 20px;
}

.markdown-content h2 {
  font-size: 18px;
}

.markdown-content h3 {
  font-size: 16px;
}

.markdown-content ul,
.markdown-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content li {
  margin: 4px 0;
}

.markdown-content code {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.code-block-wrapper {
  margin: 12px 0;
  border-radius: 6px;
  overflow: hidden;
  background: #1e1e1e;
}

.code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
}

.code-block-lang {
  font-size: 12px;
  color: #888888;
  text-transform: uppercase;
  font-weight: 600;
}

.code-block-copy {
  padding: 4px 8px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
}

.code-block-copy:hover {
  background: #1177bb;
}

.markdown-content pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  background: #1e1e1e;
}

.markdown-content pre code {
  background: none;
  padding: 0;
  font-size: 13px;
}

.streaming-cursor {
  display: inline-block;
  margin-left: 2px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 48px 24px;
  text-align: center;
  color: #888888;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #cccccc;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  max-width: 400px;
}
```

### Step 3.6: Build Verification

```bash
cd frontend
npm run build
npm run dev
```

**Manual Tests**:
1. Send message with markdown (headers, lists, code blocks)
2. Verify syntax highlighting in code blocks
3. Test streaming cursor animation during generation
4. Verify copy buttons on code blocks work
5. Check links open in new tabs
6. Test mobile responsive markdown layout

---

## Phase 004: Multi-Document Tabs

**Goal**: Enable multiple document management within a session

**Duration**: 1.5 days
**Risk**: Medium (new state management)

### Step 4.1: Create Document Types

**File**: `frontend/src/types/document.ts`

```typescript
export interface Document {
  id: string;
  title: string;
  html: string;
  createdAt: Date;
  updatedAt: Date;
  versionCount: number;
}

export interface DocumentListResponse {
  documents: Document[];
}

export interface CreateDocumentRequest {
  title: string;
}

export interface UpdateDocumentTitleRequest {
  title: string;
}
```

### Step 4.2: Create Document Service

**File**: `frontend/src/services/documentService.ts`

```typescript
import { Document, DocumentListResponse, CreateDocumentRequest } from '../types/document';

const API_BASE = '/api';

export const documentService = {
  async getDocuments(sessionId: string): Promise<Document[]> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/documents`);
    if (!response.ok) {
      throw new Error(`Failed to fetch documents: ${response.statusText}`);
    }
    const data: DocumentListResponse = await response.json();
    return data.documents.map((doc) => ({
      ...doc,
      createdAt: new Date(doc.createdAt),
      updatedAt: new Date(doc.updatedAt),
    }));
  },

  async createDocument(sessionId: string, title: string): Promise<Document> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title } as CreateDocumentRequest),
    });
    if (!response.ok) {
      throw new Error(`Failed to create document: ${response.statusText}`);
    }
    const doc = await response.json();
    return {
      ...doc,
      createdAt: new Date(doc.createdAt),
      updatedAt: new Date(doc.updatedAt),
    };
  },

  async switchDocument(sessionId: string, documentId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/documents/${documentId}/switch`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to switch document: ${response.statusText}`);
    }
  },

  async updateTitle(documentId: string, title: string): Promise<void> {
    const response = await fetch(`${API_BASE}/documents/${documentId}/title`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      throw new Error(`Failed to update title: ${response.statusText}`);
    }
  },

  async deleteDocument(sessionId: string, documentId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/documents/${documentId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete document: ${response.statusText}`);
    }
  },
};
```

### Step 4.3: Create Document Tab Component

**File**: `frontend/src/components/DocumentTabs/DocumentTab.tsx`

```typescript
import React, { useState, useRef, useEffect } from 'react';
import { Document } from '../../types/document';

interface DocumentTabProps {
  document: Document;
  isActive: boolean;
  onSelect: () => void;
  onRename: (newTitle: string) => void;
  onClose: () => void;
}

export default function DocumentTab({
  document,
  isActive,
  onSelect,
  onRename,
  onClose,
}: DocumentTabProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(document.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleDoubleClick = () => {
    if (isActive) {
      setIsEditing(true);
    }
  };

  const handleBlur = () => {
    if (editTitle.trim() && editTitle !== document.title) {
      onRename(editTitle.trim());
    } else {
      setEditTitle(document.title);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleBlur();
    } else if (e.key === 'Escape') {
      setEditTitle(document.title);
      setIsEditing(false);
    }
  };

  return (
    <div
      className={`document-tab ${isActive ? 'active' : ''}`}
      onClick={onSelect}
      onDoubleClick={handleDoubleClick}
    >
      {isEditing ? (
        <input
          ref={inputRef}
          type="text"
          className="tab-title-input"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
        />
      ) : (
        <span className="tab-title" title={document.title}>
          {document.title}
        </span>
      )}

      {document.versionCount > 1 && (
        <span className="version-badge" title={`${document.versionCount} versions`}>
          {document.versionCount}
        </span>
      )}

      <button
        className="tab-close"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        title="Close document"
      >
        ×
      </button>
    </div>
  );
}
```

### Step 4.4: Create Document Tabs Container

**File**: `frontend/src/components/DocumentTabs/DocumentTabs.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import DocumentTab from './DocumentTab';
import { Document } from '../../types/document';
import { documentService } from '../../services/documentService';

interface DocumentTabsProps {
  sessionId: string;
  activeDocumentId: string | null;
  onDocumentChange: (documentId: string) => void;
}

export default function DocumentTabs({
  sessionId,
  activeDocumentId,
  onDocumentChange,
}: DocumentTabsProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, [sessionId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await documentService.getDocuments(sessionId);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDocument = async () => {
    try {
      const newDoc = await documentService.createDocument(
        sessionId,
        `Document ${documents.length + 1}`
      );
      setDocuments([...documents, newDoc]);
      handleSelectDocument(newDoc.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create document');
    }
  };

  const handleSelectDocument = async (documentId: string) => {
    try {
      await documentService.switchDocument(sessionId, documentId);
      onDocumentChange(documentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch document');
    }
  };

  const handleRenameDocument = async (documentId: string, newTitle: string) => {
    try {
      await documentService.updateTitle(documentId, newTitle);
      setDocuments(
        documents.map((doc) =>
          doc.id === documentId ? { ...doc, title: newTitle } : doc
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename document');
    }
  };

  const handleCloseDocument = async (documentId: string) => {
    if (documents.length <= 1) {
      alert('Cannot close the last document');
      return;
    }

    const confirmed = confirm('Are you sure you want to close this document?');
    if (!confirmed) return;

    try {
      await documentService.deleteDocument(sessionId, documentId);
      const remainingDocs = documents.filter((doc) => doc.id !== documentId);
      setDocuments(remainingDocs);

      // Switch to first remaining document if active was closed
      if (documentId === activeDocumentId && remainingDocs.length > 0) {
        handleSelectDocument(remainingDocs[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close document');
    }
  };

  if (loading) {
    return <div className="document-tabs-loading">Loading documents...</div>;
  }

  if (error) {
    return (
      <div className="document-tabs-error">
        <span>⚠️ {error}</span>
        <button onClick={loadDocuments}>Retry</button>
      </div>
    );
  }

  return (
    <div className="document-tabs-container">
      <div className="document-tabs">
        {documents.map((doc) => (
          <DocumentTab
            key={doc.id}
            document={doc}
            isActive={doc.id === activeDocumentId}
            onSelect={() => handleSelectDocument(doc.id)}
            onRename={(newTitle) => handleRenameDocument(doc.id, newTitle)}
            onClose={() => handleCloseDocument(doc.id)}
          />
        ))}
      </div>
      <button className="new-document-btn" onClick={handleCreateDocument} title="New document">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  );
}
```

### Step 4.5: Add Tab Styles

**File**: `frontend/src/components/DocumentTabs/DocumentTabs.css`

```css
.document-tabs-container {
  display: flex;
  align-items: center;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  padding: 0 8px;
  overflow-x: auto;
  overflow-y: hidden;
}

.document-tabs {
  display: flex;
  flex: 1;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.document-tabs::-webkit-scrollbar {
  height: 4px;
}

.document-tabs::-webkit-scrollbar-thumb {
  background: #555555;
  border-radius: 2px;
}

.document-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #2d2d30;
  color: #cccccc;
  border-top: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  min-width: 120px;
  max-width: 200px;
}

.document-tab:hover {
  background: #323233;
}

.document-tab.active {
  background: #1e1e1e;
  border-top-color: #006FCF;
  color: #ffffff;
}

.tab-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
}

.tab-title-input {
  flex: 1;
  background: #3c3c3c;
  border: 1px solid #006FCF;
  color: #ffffff;
  padding: 2px 6px;
  font-size: 13px;
  outline: none;
  border-radius: 2px;
}

.version-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  background: #FFB900;
  color: #000000;
  font-size: 10px;
  font-weight: 600;
  border-radius: 9px;
}

.tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: none;
  border: none;
  color: #888888;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.2s;
  padding: 0;
}

.tab-close:hover {
  background: #555555;
  color: #ffffff;
}

.new-document-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: none;
  border: none;
  color: #cccccc;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.new-document-btn svg {
  width: 16px;
  height: 16px;
}

.new-document-btn:hover {
  background: #3e3e42;
  color: #ffffff;
}

.document-tabs-loading,
.document-tabs-error {
  padding: 8px 16px;
  font-size: 13px;
  color: #cccccc;
}

.document-tabs-error {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #f48771;
}

.document-tabs-error button {
  padding: 4px 8px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .document-tab {
    min-width: 100px;
    max-width: 150px;
    padding: 6px 10px;
  }

  .tab-title {
    font-size: 12px;
  }

  .version-badge {
    font-size: 9px;
    min-width: 16px;
    height: 16px;
  }
}
```

### Step 4.6: Build Verification

```bash
cd frontend
npm run build
npm run dev
```

**Manual Tests**:
1. Create new document with "+" button
2. Switch between tabs, verify content loads
3. Double-click tab to rename, press Enter to save
4. Close tab with "×" button (verify can't close last tab)
5. Verify version badge shows correct count
6. Test horizontal scrolling with many tabs
7. Check mobile responsive tab layout

---

## Phase 005: Version History Timeline

**Goal**: Add version browsing and restoration

**Duration**: 1.5 days
**Risk**: Medium (complex UI state)

### Step 5.1: Create Version Types

**File**: `frontend/src/types/version.ts`

```typescript
export interface Version {
  id: string;
  versionNumber: number;
  html: string;
  userPrompt: string;
  editSummary: string;
  createdAt: Date;
}

export interface VersionListResponse {
  versions: Version[];
}
```

### Step 5.2: Create Version Service

**File**: `frontend/src/services/versionService.ts`

```typescript
import { Version, VersionListResponse } from '../types/version';

const API_BASE = '/api';

export const versionService = {
  async getVersions(documentId: string): Promise<Version[]> {
    const response = await fetch(`${API_BASE}/documents/${documentId}/versions`);
    if (!response.ok) {
      throw new Error(`Failed to fetch versions: ${response.statusText}`);
    }
    const data: VersionListResponse = await response.json();
    return data.versions.map((v) => ({
      ...v,
      createdAt: new Date(v.createdAt),
    }));
  },

  async restoreVersion(documentId: string, versionId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/documents/${documentId}/versions/${versionId}/restore`,
      {
        method: 'POST',
      }
    );
    if (!response.ok) {
      throw new Error(`Failed to restore version: ${response.statusText}`);
    }
  },
};
```

### Step 5.3: Create Version Timeline Component

**File**: `frontend/src/components/VersionHistory/VersionTimeline.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Version } from '../../types/version';
import { versionService } from '../../services/versionService';
import VersionItem from './VersionItem';

interface VersionTimelineProps {
  documentId: string;
  currentVersionId: string;
  onVersionSelect: (version: Version) => void;
  onVersionRestore: (versionId: string) => void;
}

export default function VersionTimeline({
  documentId,
  currentVersionId,
  onVersionSelect,
  onVersionRestore,
}: VersionTimelineProps) {
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  useEffect(() => {
    loadVersions();
  }, [documentId]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const vers = await versionService.getVersions(documentId);
      setVersions(vers);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions');
    } finally {
      setLoading(false);
    }
  };

  const handleVersionClick = (version: Version) => {
    setSelectedVersionId(version.id);
    onVersionSelect(version);
  };

  const handleRestore = async (versionId: string) => {
    const confirmed = confirm('Restore this version? This will create a new version.');
    if (!confirmed) return;

    try {
      await versionService.restoreVersion(documentId, versionId);
      onVersionRestore(versionId);
      await loadVersions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore version');
    }
  };

  if (loading) {
    return (
      <div className="version-timeline-loading">
        <div className="loading-spinner" />
        <span>Loading versions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="version-timeline-error">
        <span>⚠️ {error}</span>
        <button onClick={loadVersions}>Retry</button>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="version-timeline-empty">
        <span>No version history yet</span>
      </div>
    );
  }

  return (
    <div className="version-timeline">
      <div className="version-timeline-header">
        <h4>Version History</h4>
        <span className="version-count">{versions.length} versions</span>
      </div>
      <div className="version-timeline-list">
        {versions.map((version) => (
          <VersionItem
            key={version.id}
            version={version}
            isSelected={version.id === selectedVersionId}
            isCurrent={version.id === currentVersionId}
            onClick={() => handleVersionClick(version)}
            onRestore={() => handleRestore(version.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

### Step 5.4: Create Version Item Component

**File**: `frontend/src/components/VersionHistory/VersionItem.tsx`

```typescript
import React from 'react';
import { Version } from '../../types/version';

interface VersionItemProps {
  version: Version;
  isSelected: boolean;
  isCurrent: boolean;
  onClick: () => void;
  onRestore: () => void;
}

export default function VersionItem({
  version,
  isSelected,
  isCurrent,
  onClick,
  onRestore,
}: VersionItemProps) {
  return (
    <div
      className={`version-item ${isSelected ? 'selected' : ''} ${isCurrent ? 'current' : ''}`}
      onClick={onClick}
    >
      <div className="version-item-header">
        <span className="version-number">v{version.versionNumber}</span>
        {isCurrent && <span className="current-badge">Current</span>}
        <span className="version-time">
          {version.createdAt.toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>

      {version.editSummary && (
        <div className="version-summary">{version.editSummary}</div>
      )}

      {version.userPrompt && (
        <div className="version-prompt">
          <span className="prompt-label">Prompt:</span>
          <span className="prompt-text">{version.userPrompt}</span>
        </div>
      )}

      {isSelected && !isCurrent && (
        <button className="restore-btn" onClick={(e) => {
          e.stopPropagation();
          onRestore();
        }}>
          Restore this version
        </button>
      )}
    </div>
  );
}
```

### Step 5.5: Add Version Timeline Styles

**File**: `frontend/src/components/VersionHistory/VersionTimeline.css`

```css
.version-timeline {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  border-top: 1px solid #3e3e42;
}

.version-timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
}

.version-timeline-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #cccccc;
}

.version-count {
  font-size: 12px;
  color: #888888;
}

.version-timeline-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-item {
  padding: 12px;
  margin-bottom: 8px;
  background: #252526;
  border: 1px solid #3e3e42;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.version-item:hover {
  background: #2d2d30;
  border-color: #555555;
}

.version-item.selected {
  background: #2d2d30;
  border-color: #006FCF;
  box-shadow: 0 0 0 1px #006FCF;
}

.version-item.current {
  border-color: #28CD6E;
}

.version-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.version-number {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.current-badge {
  padding: 2px 6px;
  background: #28CD6E;
  color: #000000;
  font-size: 10px;
  font-weight: 600;
  border-radius: 3px;
  text-transform: uppercase;
}

.version-time {
  margin-left: auto;
  font-size: 11px;
  color: #888888;
}

.version-summary {
  font-size: 13px;
  color: #cccccc;
  margin-bottom: 6px;
  line-height: 1.4;
}

.version-prompt {
  font-size: 12px;
  color: #888888;
  padding: 6px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  margin-bottom: 8px;
}

.prompt-label {
  font-weight: 600;
  margin-right: 4px;
}

.prompt-text {
  font-style: italic;
}

.restore-btn {
  width: 100%;
  padding: 6px 12px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 8px;
}

.restore-btn:hover {
  background: #1177bb;
}

.version-timeline-loading,
.version-timeline-error,
.version-timeline-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
  text-align: center;
  color: #888888;
  font-size: 13px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #3e3e42;
  border-top-color: #006FCF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.version-timeline-error {
  color: #f48771;
}

.version-timeline-error button {
  margin-top: 12px;
  padding: 6px 12px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .version-timeline-header {
    padding: 10px 12px;
  }

  .version-item {
    padding: 10px;
  }

  .version-summary {
    font-size: 12px;
  }

  .version-prompt {
    font-size: 11px;
  }
}
```

### Step 5.6: Build Verification

```bash
cd frontend
npm run build
npm run dev
```

**Manual Tests**:
1. Open version timeline, verify versions load
2. Click version, verify preview updates
3. Click "Restore" button, confirm dialog appears
4. Verify restored version creates new version
5. Check current version badge shows correctly
6. Test mobile responsive timeline layout

---

## Phase 006: UI Polish & Export Features

**Goal**: Add professional UI polish and export functionality

**Duration**: 1 day
**Risk**: Low (cosmetic improvements)

### Step 6.1: Create Starter Template Cards

**File**: `frontend/src/components/EmptyState/TemplateCards.tsx`

```typescript
import React from 'react';

interface Template {
  id: string;
  title: string;
  description: string;
  icon: string;
  prompt: string;
}

const TEMPLATES: Template[] = [
  {
    id: 'impact-assessment',
    title: 'Impact Assessment',
    description: 'Professional report with tabbed analysis sections',
    icon: '📊',
    prompt: 'Create an impact assessment report with tabbed navigation for Problem Statement, Technical Solutions, Risk Analysis, and Recommendations.',
  },
  {
    id: 'technical-docs',
    title: 'Technical Documentation',
    description: 'Clean documentation site with sidebar navigation',
    icon: '📚',
    prompt: 'Create technical documentation with a sidebar navigation, code examples, and clear section hierarchy.',
  },
  {
    id: 'business-dashboard',
    title: 'Business Dashboard',
    description: 'Interactive dashboard with charts and metrics',
    icon: '📈',
    prompt: 'Create a business dashboard with key metrics, charts, and data visualization components.',
  },
  {
    id: 'presentation',
    title: 'Presentation Slides',
    description: 'Clean slide deck with navigation',
    icon: '🎯',
    prompt: 'Create a presentation slide deck with navigation controls and professional styling.',
  },
  {
    id: 'project-report',
    title: 'Project Report',
    description: 'Structured report with status and milestones',
    icon: '📝',
    prompt: 'Create a project report with executive summary, status updates, milestones, and team information.',
  },
  {
    id: 'process-docs',
    title: 'Process Documentation',
    description: 'Step-by-step guide with workflows',
    icon: '🔄',
    prompt: 'Create process documentation with step-by-step workflows, decision trees, and visual guides.',
  },
];

interface TemplateCardsProps {
  onSelectTemplate: (prompt: string) => void;
}

export default function TemplateCards({ onSelectTemplate }: TemplateCardsProps) {
  return (
    <div className="template-cards-container">
      <h2 className="template-cards-title">Start with a template</h2>
      <div className="template-cards-grid">
        {TEMPLATES.map((template) => (
          <button
            key={template.id}
            className="template-card"
            onClick={() => onSelectTemplate(template.prompt)}
          >
            <div className="template-icon">{template.icon}</div>
            <div className="template-content">
              <h3 className="template-title">{template.title}</h3>
              <p className="template-description">{template.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

### Step 6.2: Create Export Dropdown

**File**: `frontend/src/components/Export/ExportDropdown.tsx`

```typescript
import React, { useState, useRef, useEffect } from 'react';

interface ExportDropdownProps {
  documentId: string;
  documentTitle: string;
}

export default function ExportDropdown({ documentId, documentTitle }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExport = async (format: 'html' | 'pptx' | 'pdf') => {
    try {
      const response = await fetch(`/api/export/${documentId}/${format}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${documentTitle}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setIsOpen(false);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    }
  };

  return (
    <div className="export-dropdown" ref={dropdownRef}>
      <button
        className="export-button"
        onClick={() => setIsOpen(!isOpen)}
        title="Export document"
      >
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
        Export
      </button>

      {isOpen && (
        <div className="export-menu">
          <button
            className="export-menu-item"
            onClick={() => handleExport('html')}
          >
            <span className="export-icon">📄</span>
            <div className="export-info">
              <div className="export-format">HTML</div>
              <div className="export-description">Single-file document</div>
            </div>
          </button>

          <button
            className="export-menu-item"
            onClick={() => handleExport('pptx')}
          >
            <span className="export-icon">📊</span>
            <div className="export-info">
              <div className="export-format">PowerPoint</div>
              <div className="export-description">PPTX presentation</div>
            </div>
          </button>

          <button
            className="export-menu-item"
            onClick={() => handleExport('pdf')}
          >
            <span className="export-icon">📕</span>
            <div className="export-info">
              <div className="export-format">PDF</div>
              <div className="export-description">Print-ready document</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
```

### Step 6.3: Create Add Visual Button

**File**: `frontend/src/components/Chat/AddVisualButton.tsx`

```typescript
import React, { useState } from 'react';

interface AddVisualButtonProps {
  onAddVisual: (prompt: string) => void;
  disabled?: boolean;
}

export default function AddVisualButton({ onAddVisual, disabled = false }: AddVisualButtonProps) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [visualPrompt, setVisualPrompt] = useState('');

  const handleSubmit = () => {
    if (visualPrompt.trim()) {
      onAddVisual(visualPrompt.trim());
      setVisualPrompt('');
      setShowPrompt(false);
    }
  };

  if (!showPrompt) {
    return (
      <button
        className="add-visual-button"
        onClick={() => setShowPrompt(true)}
        disabled={disabled}
        title="Add chart, graph, or visualization"
      >
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
        </svg>
        Add Visual
      </button>
    );
  }

  return (
    <div className="visual-prompt-input">
      <input
        type="text"
        placeholder="Describe the chart or visualization..."
        value={visualPrompt}
        onChange={(e) => setVisualPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit();
          if (e.key === 'Escape') setShowPrompt(false);
        }}
        autoFocus
      />
      <button onClick={handleSubmit} disabled={!visualPrompt.trim()}>
        Add
      </button>
      <button onClick={() => setShowPrompt(false)} className="cancel-btn">
        Cancel
      </button>
    </div>
  );
}
```

### Step 6.4: Add Polish Styles

**File**: `frontend/src/components/Polish/polish.css`

```css
/* Template Cards */
.template-cards-container {
  padding: 48px 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.template-cards-title {
  margin: 0 0 32px 0;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  text-align: center;
}

.template-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.template-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 20px;
  background: #252526;
  border: 1px solid #3e3e42;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.template-card:hover {
  background: #2d2d30;
  border-color: #006FCF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 111, 207, 0.2);
}

.template-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.template-content {
  flex: 1;
}

.template-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.template-description {
  margin: 0;
  font-size: 13px;
  color: #888888;
  line-height: 1.5;
}

/* Export Dropdown */
.export-dropdown {
  position: relative;
}

.export-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.export-button:hover {
  background: #1177bb;
}

.export-button svg {
  width: 18px;
  height: 18px;
}

.export-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 240px;
  background: #252526;
  border: 1px solid #3e3e42;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  z-index: 1000;
}

.export-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 1px solid #3e3e42;
  cursor: pointer;
  transition: background 0.2s;
  text-align: left;
}

.export-menu-item:last-child {
  border-bottom: none;
}

.export-menu-item:hover {
  background: #2d2d30;
}

.export-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.export-info {
  flex: 1;
}

.export-format {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 2px;
}

.export-description {
  font-size: 12px;
  color: #888888;
}

/* Add Visual Button */
.add-visual-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #28CD6E;
  color: #000000;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-visual-button:hover:not(:disabled) {
  background: #2ae177;
  transform: translateY(-1px);
}

.add-visual-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-visual-button svg {
  width: 16px;
  height: 16px;
}

.visual-prompt-input {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: #252526;
  border-radius: 6px;
}

.visual-prompt-input input {
  flex: 1;
  padding: 8px 12px;
  background: #1e1e1e;
  border: 1px solid #3e3e42;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  outline: none;
}

.visual-prompt-input input:focus {
  border-color: #006FCF;
}

.visual-prompt-input button {
  padding: 8px 16px;
  background: #0e639c;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.visual-prompt-input button:hover:not(:disabled) {
  background: #1177bb;
}

.visual-prompt-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.visual-prompt-input .cancel-btn {
  background: #3e3e42;
}

.visual-prompt-input .cancel-btn:hover {
  background: #555555;
}

/* Loading Animation */
.streaming-loader {
  display: flex;
  gap: 4px;
  padding: 12px;
}

.streaming-dot {
  width: 8px;
  height: 8px;
  background: #006FCF;
  border-radius: 50%;
  animation: pulse 1.4s infinite ease-in-out;
}

.streaming-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.streaming-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes pulse {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .template-cards-container {
    padding: 32px 16px;
  }

  .template-cards-title {
    font-size: 20px;
    margin-bottom: 24px;
  }

  .template-cards-grid {
    grid-template-columns: 1fr;
  }

  .export-menu {
    right: auto;
    left: 0;
  }
}
```

### Step 6.5: Remove Admin Link

**File**: `frontend/src/components/Header/Header.tsx`

Find and remove the admin link:

```typescript
// REMOVE THIS:
// <a href="/admin" className="admin-link">Admin</a>

// REMOVE WebSocket status indicator:
// {wsStatus && <div className="ws-status">{wsStatus}</div>}
```

### Step 6.6: Build Verification

```bash
cd frontend
npm run build

# Check final bundle size (should be < 2MB)
du -sh dist/

# Verify all assets compiled
ls -la dist/assets/

npm run dev
```

**Manual Tests**:
1. Click template card, verify prompt fills input
2. Test export dropdown (HTML/PPTX/PDF downloads)
3. Click "Add Visual" button, enter prompt
4. Verify copy buttons on code blocks work
5. Check no admin link in header
6. Verify no WebSocket status indicator
7. Test all features on mobile (375px width)

---

## Build Verification Checklist

After completing ALL phases:

### Bundle Verification
```bash
cd frontend
npm run build

# Check bundle size
du -sh dist/
# Expected: < 2MB total

# Check specific assets
ls -lh dist/assets/
# Verify CodeMirror is ~300KB, not Monaco's 10MB
```

### TypeScript Validation
```bash
cd frontend
npx tsc --noEmit
# Expected: 0 errors
```

### Linting
```bash
cd frontend
npm run lint
# Expected: 0 errors, minimal warnings
```

### Development Server
```bash
cd frontend
npm run dev
# Visit http://localhost:5173
# Test all phases manually
```

### Production Build Test
```bash
cd frontend
npm run build
npm run preview
# Visit http://localhost:4173
# Test production build functionality
```

---

## Testing Scenarios

### Scenario 1: Basic SSE Chat
1. Start app, create new session
2. Send message: "Create a simple HTML page with a header"
3. Verify SSE connection in DevTools Network tab
4. Verify status updates appear during generation
5. Verify HTML preview renders correctly
6. Verify chat message shows markdown summary

**Expected**: SSE stream processes without errors, HTML renders, markdown displays

### Scenario 2: Code Viewing
1. Generate HTML document
2. Toggle to code view
3. Verify syntax highlighting appears
4. Click copy button
5. Paste in text editor
6. Verify complete HTML was copied

**Expected**: CodeMirror highlights HTML, copy works perfectly

### Scenario 3: Multi-Document Workflow
1. Create new document with "+" button
2. Switch between documents
3. Rename document by double-clicking tab
4. Create 5+ documents, test horizontal scrolling
5. Close documents (verify can't close last one)
6. Verify version badges show correct counts

**Expected**: All tab operations work smoothly, content persists

### Scenario 4: Version History
1. Make 5 edits to a document
2. Open version timeline
3. Click previous version, verify preview updates
4. Click "Restore" on old version
5. Verify new version created
6. Check version count badge incremented

**Expected**: Time-travel works, restoration creates new version

### Scenario 5: Export Functionality
1. Generate complete HTML document
2. Click export dropdown
3. Export as HTML (verify download)
4. Export as PPTX (verify download)
5. Export as PDF (verify download)
6. Open each file, verify content correct

**Expected**: All formats download and open correctly

### Scenario 6: Template Cards
1. Start with empty session
2. Click "Technical Documentation" template card
3. Verify prompt fills input
4. Send prompt, verify document generates
5. Repeat with different template
6. Verify each template produces expected structure

**Expected**: Templates populate prompts, generate appropriate documents

### Scenario 7: Error Handling
1. Stop backend server
2. Send chat message
3. Verify error banner appears
4. Dismiss error banner
5. Restart backend
6. Retry message
7. Verify works after reconnection

**Expected**: Graceful error handling, recovery works

### Scenario 8: Mobile Responsive
1. Resize browser to 375px width
2. Test chat interface scrolling
3. Test code view scrolling
4. Test document tabs horizontal scroll
5. Test version timeline mobile layout
6. Test template cards mobile layout

**Expected**: All layouts adapt properly, no broken UI

### Scenario 9: Performance Test
1. Generate large document (10+ sections)
2. Switch to code view
3. Verify CodeMirror loads quickly
4. Create 10 versions of document
5. Load version timeline
6. Verify timeline loads quickly
7. Switch between versions
8. Verify switching is responsive

**Expected**: No lag, smooth transitions

### Scenario 10: Long Session Test
1. Work for 15 minutes continuously
2. Make 10+ edits to documents
3. Switch between 5 documents
4. Check browser memory usage
5. Verify no memory leaks
6. Verify all data persists

**Expected**: Stable performance, no degradation

---

## Rollback Plan

### If Phase 001 Fails (SSE)
**Problem**: SSE connection errors, streaming doesn't work

**Rollback Steps**:
```bash
cd frontend
git checkout main
git checkout -b rollback-phase-001
git revert <commit-hash-of-phase-001>
npm install
npm run build
```

**Alternative**: Keep WebSocket code in `feature/websocket-backup` branch, switch back

### If Phase 002 Fails (CodeMirror)
**Problem**: CodeMirror breaks build, bundle too large

**Rollback Steps**:
```bash
npm uninstall @codemirror/view @codemirror/state @codemirror/lang-html @codemirror/theme-one-dark
git checkout main -- src/components/CodeViewer/
npm install
npm run build
```

**Fallback**: Use simple `<pre>` tag with copy button, no syntax highlighting

### If Phase 003 Fails (Markdown)
**Problem**: Markdown rendering breaks, streaming flickers

**Rollback Steps**:
```bash
npm uninstall react-markdown remark-gfm rehype-highlight
git checkout main -- src/components/Chat/ChatMessage.tsx
npm install
npm run build
```

**Fallback**: Plain text chat messages (original behavior)

### If Phase 004 Fails (Multi-Document)
**Problem**: Document switching errors, data loss

**Rollback Steps**:
```bash
git checkout main -- src/components/DocumentTabs/
git checkout main -- src/services/documentService.ts
npm install
npm run build
```

**Fallback**: Single document per session (original behavior)

### If Phase 005 Fails (Version History)
**Problem**: Version loading errors, restore failures

**Rollback Steps**:
```bash
git checkout main -- src/components/VersionHistory/
git checkout main -- src/services/versionService.ts
npm install
npm run build
```

**Fallback**: No version history (users live with current state only)

### If Phase 006 Fails (Polish)
**Problem**: Export broken, UI glitches

**Rollback Steps**:
```bash
git checkout main -- src/components/EmptyState/
git checkout main -- src/components/Export/
npm install
npm run build
```

**Fallback**: Manual HTML download only, no templates

### Complete Rollback
**If everything fails, restore to pre-004 state**:

```bash
cd frontend
git checkout main
git branch -D feature/004-frontend-enhancements
npm install
npm run build
```

**Verify rollback**:
```bash
npm run dev
# Test original WebSocket functionality
# Verify app works as before
```

---

## Post-Implementation Validation

### Performance Metrics
- [ ] Bundle size < 2MB
- [ ] Initial load time < 3 seconds
- [ ] SSE connection time < 500ms
- [ ] Code view render time < 1 second
- [ ] Version timeline load time < 2 seconds

### Code Quality
- [ ] TypeScript: 0 errors
- [ ] ESLint: 0 errors
- [ ] No `console.log` in production code
- [ ] All async operations have error handling
- [ ] All user actions have loading states

### Browser Compatibility
- [ ] Chrome 120+ ✅
- [ ] Firefox 120+ ✅
- [ ] Safari 17+ ✅
- [ ] Edge 120+ ✅

### Mobile Responsive
- [ ] 375px (iPhone SE) ✅
- [ ] 768px (iPad) ✅
- [ ] 1024px (iPad Pro) ✅
- [ ] 1920px (Desktop) ✅

### Accessibility
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Screen reader compatible (ARIA labels)
- [ ] Color contrast ratios meet WCAG AA

---

## Sign-off Checklist

Before marking Plan 004 as COMPLETE:

### Technical Validation
- [ ] All 6 phases completed in order
- [ ] Build passes with 0 errors
- [ ] Bundle size verified < 2MB
- [ ] TypeScript validation passes
- [ ] ESLint passes with no errors
- [ ] All dependencies locked in package.json

### Functional Testing
- [ ] All 10 testing scenarios pass
- [ ] SSE streaming works reliably
- [ ] CodeMirror syntax highlighting works
- [ ] Markdown rendering works during streaming
- [ ] Multi-document tabs work correctly
- [ ] Version history works (load, preview, restore)
- [ ] Export works (HTML, PPTX, PDF)
- [ ] Template cards work
- [ ] Error handling works gracefully
- [ ] Mobile responsive verified on 4 sizes

### Integration Testing
- [ ] Backend Plan 001 endpoints working
- [ ] SSE events parse correctly
- [ ] Document switching preserves state
- [ ] Version restoration creates new version
- [ ] Export generates valid files
- [ ] Redis session storage working

### Documentation
- [ ] CHANGELOG.md updated with new features
- [ ] Breaking changes documented
- [ ] Migration guide written (WebSocket → SSE)
- [ ] API integration notes updated
- [ ] User-facing features documented

### Deployment Readiness
- [ ] Production build tested
- [ ] Environment variables documented
- [ ] Rollback plan tested
- [ ] Performance metrics validated
- [ ] Security review completed

### Final Approval
- [ ] Code reviewed by senior developer
- [ ] UX reviewed by designer
- [ ] QA testing completed
- [ ] Stakeholder demo completed
- [ ] Ready for production deployment

---

**Sign-off**: ___________________________
**Date**: ___________________________
**Reviewer**: ___________________________

---

## Dependencies for Next Plans

**Plan 005 (Admin Dashboard v2)** can start when:
- ✅ Plan 001 (Backend Foundation) complete
- ✅ Plan 004 (Frontend Enhancements) complete
- Backend analytics endpoints verified
- Frontend SSE working reliably

**Plan 006 (AI Enhancements)** can start when:
- ✅ Plan 001 (Backend Foundation) complete
- ✅ Plan 004 (Frontend Enhancements) complete
- Multi-document architecture stable
- Version history working correctly

---

**End of Implementation Plan 004**
