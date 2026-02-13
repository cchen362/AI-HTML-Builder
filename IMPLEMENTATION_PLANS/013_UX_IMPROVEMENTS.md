# Implementation Plan 013: UX Improvements

## Status: COMPLETE

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 012 (Architecture Refactoring) is FULLY complete (it is)
- You have read this ENTIRE document end-to-end
- You understand every file path, code change, and verification step

**STRICT RULES — FOLLOW EXACTLY:**
1. Implement phases IN ORDER (1 → 2 → 3 → 4 → 5 → 6). Do NOT skip phases or reorder.
2. Run verification after EACH phase before proceeding to the next.
3. Every new CSS MUST use `var(--*)` tokens from `frontend/src/theme.css`. ZERO hardcoded colors, fonts, or sizes.
4. Do NOT create files not listed in this plan. Do NOT delete files not listed in this plan.
5. Do NOT modify the surgical editing engine (`editor.py`, `fuzzy_match.py`) or database schema.
6. Do NOT add dependencies to `package.json` or `requirements.txt`.
7. Preserve the "Obsidian Terminal" aesthetic — dark theme, monospace accents, uppercase labels.
8. All new components must work in BOTH dark mode (default) and light mode (`[data-theme="light"]`).

**CONTEXT:**
A UX review agent scored the frontend 5/10. The core engineering is solid, but friction points affect daily usage. This plan addresses 10 high-impact items (2 original items skipped after user workshop). All design decisions have been workshopped and finalized with the user.

**DEPENDENCIES:**
- Plans 001-012 (all complete)

**ESTIMATED EFFORT:** 2-3 days

---

## Design Cohesion Rules (MANDATORY)

Every new visual element MUST use the existing design system in `frontend/src/theme.css`.

| Element | Tokens |
|---------|--------|
| Fonts | `--font-mono` (actions/labels/badges), `--font-display` (headings), `--font-body` (body) |
| Colors | All via `var(--*)`. Accent: `--accent-primary`. Surfaces: `--surface-overlay` (modals), `--surface-raised` (cards), `--surface-highlight` (hover). Signals: `--signal-error`, `--signal-active`, `--signal-warning` |
| Primary buttons | `--gradient-send-btn` bg + `--text-inverse` color |
| Secondary buttons | `transparent` bg + `--border-default` border + `--text-secondary` color |
| Danger buttons | `--signal-error` based gradient |
| Shadows | `--shadow-sm`, `--shadow-md`, `--shadow-lg` |
| Radii | `--radius-sm` (4px), `--radius-md` (8px), `--radius-lg` (12px), `--radius-full` (pills) |
| Motion | `--duration-fast` (150ms hover), `--duration-normal` (250ms transitions), `--ease-out-expo` |
| Keyframes | Reuse existing: `modal-enter`, `dropdown-enter`, `card-enter`, `fade-up`, `fade-pulse`, `summon-pulse` |
| Labels | UPPERCASE, `--font-mono`, `--tracking-wide`, `--fs-xs`/`--fs-sm` |
| Status text | `--text-tertiary`, `--font-mono`, `--fs-xs`, `--tracking-widest` |

**NEVER:** hardcode hex values, declare `font-family`, use `px` font sizes, create new keyframes (unless essential).

---

## Phase 1: Zero-Risk Fixes (Items 1a, 3b)

Two surgical fixes with zero UI changes. Combined because both are <5 lines each.

### Step 1.1: Pass `activeDocument.id` to `sendMessage`

**File:** `frontend/src/App.tsx`

**Current code (line ~182):**
```typescript
const handleSendMessage = useCallback((message: string) => {
  if (message.trim()) {
    setError(null)
    sendMessage(message)
  }
}, [sendMessage])
```

**Change to:**
```typescript
const handleSendMessage = useCallback((message: string) => {
  if (message.trim()) {
    setError(null)
    sendMessage(message, activeDocument?.id)
  }
}, [sendMessage, activeDocument])
```

**Why:** Prevents editing the wrong document during fast document switches. `sendMessage` already accepts `documentId` as second param (see `useSSEChat.ts` line 147).

### Step 1.2: Send Button Debounce

**File:** `frontend/src/hooks/useSSEChat.ts`

Add ref near other refs (after line 40):
```typescript
const sendingRef = useRef(false);
```

In `sendMessage` callback (line 147), add guard at the very start:
```typescript
const sendMessage = useCallback(async (content: string, documentId?: string) => {
  const sid = sessionIdRef.current;
  if (!sid || !content.trim() || sendingRef.current) return;
  sendingRef.current = true;
  // ... rest of existing code ...
```

In the `finally` block (line ~273), add unlock:
```typescript
} finally {
  setIsStreaming(false);
  abortRef.current = null;
  sendingRef.current = false;  // ADD THIS LINE
}
```

**Why:** Prevents double-click or double Ctrl+Enter from firing duplicate requests.

### Phase 1 Verification

```bash
cd frontend && npm run build    # TypeScript + Vite clean
cd frontend && npm run lint     # ESLint clean
```

Manual: Open Network tab, send message → verify `document_id` in POST body. Rapidly click send → only one request fires.

---

## Phase 2: Styled Confirm Dialog (Item 2b)

Reusable themed modal component. Required by Phases 4-6.

### Step 2.1: Create ConfirmDialog Component

**New file:** `frontend/src/components/ConfirmDialog/ConfirmDialog.tsx`

```typescript
import { useEffect, useCallback } from 'react';
import './ConfirmDialog.css';

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  danger = false,
}: ConfirmDialogProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onCancel();
  }, [onCancel]);

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-header">
          <h3>{title}</h3>
        </div>
        <div className="confirm-body">
          <p>{message}</p>
        </div>
        <div className="confirm-actions">
          <button className="confirm-cancel-btn" onClick={onCancel}>
            {cancelText}
          </button>
          <button
            className={`confirm-action-btn${danger ? ' danger' : ''}`}
            onClick={() => { onConfirm(); onCancel(); }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Step 2.2: Create ConfirmDialog CSS

**New file:** `frontend/src/components/ConfirmDialog/ConfirmDialog.css`

```css
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fade-up var(--duration-normal) var(--ease-out-expo);
}

.confirm-modal {
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 380px;
  max-width: 480px;
  animation: modal-enter var(--duration-normal) var(--ease-out-expo);
}

.confirm-header {
  padding: 1.25rem 1.5rem 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
}

.confirm-header h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--fs-lg);
  font-weight: var(--fw-bold);
  color: var(--text-primary);
}

.confirm-body {
  padding: 1.25rem 1.5rem;
}

.confirm-body p {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--fs-base);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 1.5rem 1.25rem;
  justify-content: flex-end;
  border-top: 1px solid var(--border-subtle);
}

.confirm-cancel-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.confirm-cancel-btn:hover {
  background: var(--surface-highlight);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.confirm-action-btn {
  background: var(--gradient-send-btn);
  border: none;
  color: var(--text-inverse);
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.confirm-action-btn:hover {
  background: var(--gradient-send-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.confirm-action-btn.danger {
  background: linear-gradient(135deg, var(--signal-error) 0%, #CC2B47 100%);
}

.confirm-action-btn.danger:hover {
  filter: brightness(1.15);
}
```

**NOTE on `.danger` gradient:** The `#CC2B47` is a darker shade of `--signal-error` for the gradient endpoint. This is the ONE permitted hardcoded color since CSS `var()` cannot be used inside gradient color-stop calculations. In light mode, `--signal-error` changes to `#DC2626`, so the gradient will adapt via the first stop.

### Step 2.3: Replace `window.confirm()` in DocumentTabs

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.tsx`

Add import at top:
```typescript
import { useState } from 'react';  // ensure useState is imported
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
```

Add state inside component:
```typescript
const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; docId: string | null }>({
  isOpen: false,
  docId: null,
});
```

Replace the `handleDelete` function (currently line ~54):
```typescript
const handleDelete = (e: React.MouseEvent, docId: string) => {
  e.stopPropagation();
  setDeleteConfirm({ isOpen: true, docId });
};
```

Add ConfirmDialog at the end of the JSX return, inside the `document-tabs-container`:
```typescript
<ConfirmDialog
  isOpen={deleteConfirm.isOpen}
  title="Delete Document?"
  message="This cannot be undone. All versions will be permanently deleted."
  onConfirm={() => {
    if (deleteConfirm.docId && onDeleteDocument) {
      onDeleteDocument(deleteConfirm.docId);
    }
  }}
  onCancel={() => setDeleteConfirm({ isOpen: false, docId: null })}
  confirmText="Delete"
  cancelText="Keep Document"
  danger
/>
```

### Step 2.4: Replace `window.confirm()` in VersionTimeline

**File:** `frontend/src/components/VersionHistory/VersionTimeline.tsx`

Add import:
```typescript
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
```

Add state inside component:
```typescript
const [restoreConfirm, setRestoreConfirm] = useState(false);
```

Replace the restore button's `onClick` (currently line ~110):
```typescript
<button
  className="restore-version-btn"
  onClick={() => setRestoreConfirm(true)}
  type="button"
>
  Restore this version
</button>
```

Add ConfirmDialog at end of JSX return, inside `version-timeline`:
```typescript
<ConfirmDialog
  isOpen={restoreConfirm}
  title={`Restore to Version ${selectedVersion}?`}
  message={`This will create a new version (v${latestVersion + 1}) with the content from v${selectedVersion}. Your current version will remain in history.`}
  onConfirm={() => {
    if (selectedVersion !== null) {
      onRestoreVersion(selectedVersion);
    }
  }}
  onCancel={() => setRestoreConfirm(false)}
  confirmText="Restore"
  cancelText="Cancel"
/>
```

**Key detail:** The message is educational — it explains that restore creates a NEW version, not time-travel. This was specifically requested by the user to prevent confusion about version numbering.

### Phase 2 Verification

```bash
cd frontend && npm run build
cd frontend && npm run lint
```

Manual: Delete a document (when 2+ exist) → verify themed dialog appears with red "Delete" button. Preview a version → click "Restore this version" → verify themed dialog with educational message and accent "Restore" button. Press Escape → dialog closes. Click backdrop → dialog closes.

---

## Phase 3: Template Badge System (Item 2c)

Replaces the original "collapse long messages" approach with a smarter template UX. When a user selects a template, instead of dumping 30+ lines into the textarea, a badge appears above the textarea and the input stays clean. Clicking the badge name opens an inline popover to preview the template ("what did I pick again?").

### How It Works (User Flow)

1. User opens Prompt Library → selects "Stakeholder Brief" → clicks "Use This Template"
2. **BEFORE (old):** Full 30-line template text dumped into textarea
3. **AFTER (new):** Small badge `📋 Stakeholder Brief [×]` appears above textarea. Textarea stays empty for user's content.
4. User types their notes/content + any extra instructions (e.g., "use dark blue theme")
5. **Click badge name** → inline popover shows template preview (click outside or Escape to dismiss)
6. On send: system prepends template instructions to user's content → full prompt goes to AI
7. Chat displays: `📋 Stakeholder Brief` badge + user's content only (template instructions hidden)
8. The `[×]` on the badge removes the template (handles accidental clicks). Textarea text is preserved. User can re-open Prompt Library to select another template.

### Step 3.1: Add Template Fields to ChatMessage Type

**File:** `frontend/src/types/index.ts`

Add two optional fields to the `ChatMessage` interface:
```typescript
export interface ChatMessage {
  id: number;
  session_id: string;
  document_id: string | null;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type: string;
  created_at: string;
  templateName?: string;    // NEW: set when message used a template
  userContent?: string;     // NEW: just the user's typed content (without template prefix)
}
```

### Step 3.2: Add TemplatePopover Inline Component

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

Define `TemplatePopover` above the `ChatInput` component (after `useAutosizeTextArea`). This inline component shows a quick preview of the selected template's instructions when the user clicks the badge name.

```typescript
// Inline popover for template preview ("what did I pick?")
const TemplatePopover: React.FC<{
  template: PromptTemplate;
  onClose: () => void;
}> = ({ template, onClose }) => {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    // Delay listener to avoid immediate close from the click that opened it
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const previewText = template.template
    .replace(/\{\{[A-Z_]+\}\}/g, '[Your content here]');

  return (
    <div className="template-popover" ref={popoverRef}>
      <div className="template-popover-header">
        <span className="template-popover-title">{template.name}</span>
        <span className="template-popover-category">{template.category}</span>
      </div>
      <div className="template-popover-body">
        {previewText.split('\n').map((line, i) => (
          <div key={i} className={
            /^[A-Z][A-Z _/&()-]+:/.test(line) ? 'popover-section-header' : 'popover-line'
          }>
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Step 3.3: Update ChatInput for Badge System + Popover

**File:** `frontend/src/components/ChatWindow/ChatInput.tsx`

**Change the `onSendMessage` prop signature** to include optional template metadata:
```typescript
interface ChatInputProps {
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string) => void;
  // ... rest unchanged
}
```

**Add new state** (near existing state declarations):
```typescript
const [activeTemplate, setActiveTemplate] = useState<PromptTemplate | null>(null);
const [popoverOpen, setPopoverOpen] = useState(false);
```

**Replace `handleTemplateSelect`** (currently line ~108):
```typescript
const handleTemplateSelect = (template: PromptTemplate) => {
  setActiveTemplate(template);
  setPopoverOpen(false);
  setMessage('');
  setAttachedFile(null);  // Clear any attached file to avoid ghost indicators
  setTimeout(() => textareaRef.current?.focus(), 100);
};
```

**Update `handleSubmit`** (currently line ~79):
```typescript
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (isProcessing) return;

  if (activeTemplate) {
    // Compose full message: template instructions + user content
    const userContent = message.trim();
    const fullMessage = userContent
      ? `${activeTemplate.template}\n\n${userContent}`
      : activeTemplate.template;
    onSendMessage(fullMessage, undefined, activeTemplate.name, userContent || '(template only)');
    setMessage('');
    setActiveTemplate(null);
    setPopoverOpen(false);
    setShowLargeContentHint(false);
    setAttachedFile(null);
  } else if (message.trim()) {
    onSendMessage(message.trim());
    setMessage('');
    setShowLargeContentHint(false);
    setAttachedFile(null);
  }
};
```

**Add template badge JSX** inside the form, before the `input-wrapper` div. Badge name is **clickable** (toggles popover):
```typescript
{activeTemplate && (
  <div className="template-badge-bar">
    <div className="template-badge">
      <span className="template-badge-icon">📋</span>
      <span
        className="template-badge-name"
        role="button"
        tabIndex={0}
        onClick={() => setPopoverOpen(prev => !prev)}
        onKeyDown={(e) => { if (e.key === 'Enter') setPopoverOpen(prev => !prev); }}
      >
        {activeTemplate.name}
      </span>
      <button
        type="button"
        className="template-badge-remove"
        onClick={handleRemoveTemplate}
        title="Remove template"
      >
        ×
      </button>
    </div>
    {popoverOpen && (
      <TemplatePopover
        template={activeTemplate}
        onClose={() => setPopoverOpen(false)}
      />
    )}
  </div>
)}
```

**Update the submit button disabled condition** — allow send when `activeTemplate` is set even without typed content:
```typescript
<button
  type="submit"
  disabled={(!message.trim() && !activeTemplate) || isProcessing}
  className="send-button"
  // ...
>
```

**Update placeholder** when template is active:
```typescript
<textarea
  // ...
  placeholder={activeTemplate
    ? `Add your content for "${activeTemplate.name}"... (or send directly to use template defaults)`
    : placeholder
  }
  // ...
/>
```

### Step 3.4: Add Template Badge + Popover CSS

**File:** `frontend/src/components/ChatWindow/ChatInput.css`

Add at the end of the file:
```css
/* --- Template Badge --- */
.template-badge-bar {
  padding: 0.5rem 0.75rem 0;
  position: relative;
}

.template-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--accent-primary-muted);
  border: 1px solid var(--accent-primary);
  border-radius: var(--radius-full);
  padding: 0.375rem 0.75rem;
  animation: card-enter var(--duration-normal) var(--ease-out-expo);
}

.template-badge-icon {
  font-size: var(--fs-sm);
  line-height: 1;
}

.template-badge-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: color var(--duration-fast);
}

.template-badge-name:hover {
  color: var(--accent-primary-hover);
  text-decoration: underline;
}

.template-badge-remove {
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: var(--fs-md);
  cursor: pointer;
  padding: 0 0.125rem;
  line-height: 1;
  transition: color var(--duration-fast);
}

.template-badge-remove:hover {
  color: var(--signal-error);
}

/* --- Template Popover (inline preview) --- */
.template-popover {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0.75rem;
  z-index: 100;
  width: 400px;
  max-height: 320px;
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: dropdown-enter var(--duration-normal) var(--ease-out-expo);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.template-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-raised);
  flex-shrink: 0;
}

.template-popover-title {
  font-family: var(--font-display);
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
  color: var(--text-primary);
}

.template-popover-category {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  background: var(--accent-primary-muted);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
}

.template-popover-body {
  padding: 0.75rem 1rem;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  line-height: var(--leading-normal);
  color: var(--text-secondary);
  flex: 1;
  min-height: 0;
}

.popover-section-header {
  font-weight: var(--fw-bold);
  color: var(--accent-primary);
  margin: 0.75rem 0 0.25rem 0;
}

.popover-section-header:first-child {
  margin-top: 0;
}

.popover-line {
  margin: 0.125rem 0;
  color: var(--text-tertiary);
}

@media (max-width: 480px) {
  .template-popover {
    width: calc(100vw - 3rem);
    max-width: 400px;
  }
}
```

### Step 3.5: Update ChatWindow to Pass Template Metadata

**File:** `frontend/src/components/ChatWindow/index.tsx`

Update the `ChatWindowProps` interface:
```typescript
interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string) => void;
  // ... rest unchanged
}
```

The `onSendMessage` prop is passed directly to `ChatInput`, so the additional parameters automatically flow through.

### Step 3.6: Update App.tsx to Handle Template Metadata

**File:** `frontend/src/App.tsx`

Update `handleSendMessage`:
```typescript
const handleSendMessage = useCallback((message: string, _files?: File[], templateName?: string, userContent?: string) => {
  if (message.trim()) {
    setError(null)
    sendMessage(message, activeDocument?.id, templateName, userContent)
  }
}, [sendMessage, activeDocument])
```

### Step 3.7: Update useSSEChat to Store Template Metadata

**File:** `frontend/src/hooks/useSSEChat.ts`

Update `sendMessage` signature and the `UseSSEChatReturn` interface:
```typescript
sendMessage: (content: string, documentId?: string, templateName?: string, userContent?: string) => Promise<void>;
```

In the `sendMessage` callback, update the function signature:
```typescript
const sendMessage = useCallback(async (content: string, documentId?: string, templateName?: string, userContent?: string) => {
```

Update the optimistic user message creation:
```typescript
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
```

### Step 3.8: Update MessageList to Display Template Badge

**File:** `frontend/src/components/ChatWindow/MessageList.tsx`

In the user message rendering section (currently line ~60-65), wrap the content:
```typescript
<div className="message-content">
  {message.role === 'assistant' ? (
    <StreamingMarkdown content={message.content} />
  ) : message.templateName ? (
    <div className="message-template-display">
      <div className="message-template-badge">
        <span className="message-template-icon">📋</span>
        <span className="message-template-name">{message.templateName}</span>
      </div>
      <div className="message-user-content">{message.userContent || ''}</div>
    </div>
  ) : (
    message.content
  )}
</div>
```

### Step 3.9: Add Message Template Display CSS

**File:** `frontend/src/components/ChatWindow/MessageList.css`

Add at end:
```css
/* --- Template Message Display --- */
.message-template-display {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.message-template-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  background: var(--accent-primary-muted);
  border-radius: var(--radius-full);
  padding: 0.25rem 0.625rem;
  width: fit-content;
}

.message-template-icon {
  font-size: var(--fs-xs);
  line-height: 1;
}

.message-template-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.message-user-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}
```

### Phase 3 Verification

```bash
cd frontend && npm run build
cd frontend && npm run lint
```

Manual test:
1. Open Prompt Library → select "Stakeholder Brief" → click "Use This Template"
2. Verify: badge `📋 STAKEHOLDER BRIEF [×]` appears above textarea, textarea is empty
3. Type "Here are my Q3 notes..." → verify textarea has just your text
4. Click badge name → verify inline popover shows template preview with section headers
5. Click outside popover → verify it closes. Press Escape → verify it closes.
6. Click `×` on badge → verify badge removed, textarea keeps your text
7. Re-open Prompt Library → select a different template → verify new badge replaces old
8. Type content → hit send
9. Verify chat shows: template badge + your content only (NOT the 30-line template instructions)
10. Verify AI response is correct (it received the full prompt behind the scenes)
11. Send template with no typed content → verify badge shows in chat without user content text

---

## Phase 4: New Session & Initial Loading (Items 1b, 2d)

### Step 4.1: Add `startNewSession` and `isInitializing` to useSSEChat

**File:** `frontend/src/hooks/useSSEChat.ts`

Add new state (near existing state declarations):
```typescript
const [isInitializing, setIsInitializing] = useState(true);
```

Update the `init()` function — wrap existing logic with isInitializing:
```typescript
async function init() {
  try {
    // ... ALL existing init code stays exactly the same ...
  } catch (err) {
    if (!cancelled && onError) {
      onError(err instanceof Error ? err.message : 'Failed to initialize session');
    }
  } finally {
    if (!cancelled) setIsInitializing(false);  // ADD THIS
  }
}
```

Add `startNewSession` method (after `cancelRequest`):
```typescript
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
```

Update `UseSSEChatReturn` interface and return object:
```typescript
interface UseSSEChatReturn {
  // ... existing ...
  isInitializing: boolean;     // ADD
  startNewSession: () => Promise<void>;  // ADD
}

return {
  // ... existing ...
  isInitializing,
  startNewSession,
};
```

### Step 4.2: Add Initial Loading Screen to App.tsx

**File:** `frontend/src/App.tsx`

Destructure new values from hook:
```typescript
const {
  // ... existing ...
  isInitializing,
  startNewSession,
} = useSSEChat({
  onError: (msg) => setError(msg),
})
```

Add loading screen before the SplitPane return (in `ChatApp` component):
```typescript
if (isInitializing) {
  return (
    <div className="App">
      <div className="app-loading">
        <div className="loading-glyph">[█]</div>
        <div className="loading-text">INITIALIZING...</div>
      </div>
    </div>
  );
}
```

### Step 4.3: Add Loading Screen CSS

**File:** `frontend/src/App.css`

Add at end:
```css
/* --- Initial Loading Screen --- */
.app-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 1.5rem;
  background: var(--surface-void);
}

.loading-glyph {
  font-family: var(--font-mono);
  font-size: var(--fs-display);
  font-weight: var(--fw-heavy);
  color: var(--accent-primary);
  animation: summon-pulse 2s ease-in-out infinite;
}

.loading-text {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  animation: fade-pulse 2s ease-in-out infinite;
}
```

### Step 4.4: Add Three-Dot Menu to ChatWindow

**File:** `frontend/src/components/ChatWindow/index.tsx`

Add imports:
```typescript
import React, { useState, useCallback, useEffect, useRef } from 'react';
```

Update props interface:
```typescript
interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string) => void;
  isStreaming?: boolean;
  currentStatus?: string;
  streamingContent?: string;
  error?: string | null;
  onDismissError?: () => void;
  onCancelRequest?: () => void;
  sessionId?: string | null;           // NEW
  onStartNewSession?: () => void;      // NEW
}
```

Add destructuring + state inside component:
```typescript
const ChatWindow: React.FC<ChatWindowProps> = ({
  // ... existing ...
  sessionId,
  onStartNewSession,
}) => {
  const [pendingTemplate, setPendingTemplate] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);  // NEW
  const menuRef = useRef<HTMLDivElement>(null);      // NEW
```

Add click-outside handler:
```typescript
useEffect(() => {
  if (!menuOpen) return;
  const handleClickOutside = (e: MouseEvent) => {
    if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
      setMenuOpen(false);
    }
  };
  // Use timeout to prevent the open-click from immediately closing
  const timer = setTimeout(() => {
    document.addEventListener('click', handleClickOutside);
  }, 0);
  return () => {
    clearTimeout(timer);
    document.removeEventListener('click', handleClickOutside);
  };
}, [menuOpen]);
```

Replace the header JSX:
```typescript
<div className="chat-header">
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <h2>AI HTML Builder</h2>
    <div className="header-actions">
      <ThemeToggle />
      <div className="header-menu-wrapper" ref={menuRef}>
        <button
          className={`header-menu-btn${menuOpen ? ' active' : ''}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Session menu"
          type="button"
        >
          ⋮
        </button>
        {menuOpen && (
          <div className="header-menu-dropdown">
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onStartNewSession?.();
              }}
              disabled={isStreaming}
            >
              New Session
            </button>
            <div className="session-id-display">
              Session: {sessionId?.slice(0, 8) || '—'}
            </div>
          </div>
        )}
      </div>
    </div>
  </div>
  <div className="session-info">
    <div className={`status-indicator ${isStreaming ? 'processing' : 'ready'}`}>
      {isStreaming ? `[>] ${currentStatus || 'PROCESSING...'}` : '[*] SYSTEMS NOMINAL'}
    </div>
  </div>
</div>
```

### Step 4.5: Add Menu CSS

**File:** `frontend/src/components/ChatWindow/ChatWindow.css`

Add at end:
```css
/* --- Header Actions & Menu --- */
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-menu-wrapper {
  position: relative;
}

.header-menu-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-md);
  line-height: 1;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.header-menu-btn:hover,
.header-menu-btn.active {
  background: var(--surface-highlight);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.header-menu-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 200px;
  z-index: 1000;
  animation: dropdown-enter var(--duration-normal) var(--ease-out-expo);
  overflow: hidden;
}

.header-menu-dropdown button {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.header-menu-dropdown button:hover:not(:disabled) {
  background: var(--surface-highlight);
}

.header-menu-dropdown button:disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
}

.session-id-display {
  padding: 0.5rem 1rem;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
}
```

### Step 4.6: Wire New Session in App.tsx

**File:** `frontend/src/App.tsx`

Add state for the confirm dialog:
```typescript
const [newSessionConfirm, setNewSessionConfirm] = useState(false);
```

Add import for ConfirmDialog:
```typescript
import ConfirmDialog from './components/ConfirmDialog/ConfirmDialog';
```

Add handler:
```typescript
const handleStartNewSession = useCallback(() => {
  setNewSessionConfirm(true);
}, []);

const confirmNewSession = useCallback(async () => {
  await startNewSession();
}, [startNewSession]);
```

Pass to ChatWindow:
```typescript
<ChatWindow
  // ... existing props ...
  sessionId={sessionId}
  onStartNewSession={handleStartNewSession}
/>
```

Add ConfirmDialog at the end of the `ChatApp` return, just before the closing `</div>`:
```typescript
<ConfirmDialog
  isOpen={newSessionConfirm}
  title="Start New Session?"
  message="Your current documents will remain accessible via session history. A fresh workspace will be created."
  onConfirm={confirmNewSession}
  onCancel={() => setNewSessionConfirm(false)}
  confirmText="Start Fresh"
  cancelText="Stay Here"
/>
```

### Phase 4 Verification

```bash
cd frontend && npm run build
cd frontend && npm run lint
```

Manual test:
1. Hard refresh → verify `[█] INITIALIZING...` screen appears briefly → app loads
2. Click three-dot menu (⋮) → verify dropdown with "New Session" + session ID
3. Click "New Session" → verify styled confirm dialog
4. Confirm → verify fresh session (empty chat, template cards visible)
5. Verify menu disabled during streaming
6. Press Escape → verify dialog closes

---

## Phase 5: Editable CodeMirror (Item 1c)

Read-only by default. Pencil icon toggle enables editing. Save/Discard in top bar.

### Step 5.1: Backend — Add `save_manual_edit` Method

**File:** `backend/app/services/session_service.py`

Add method to `SessionService` class:
```python
async def save_manual_edit(
    self, document_id: str, html_content: str
) -> int:
    """Save a manual HTML edit as a new version."""
    return await self.save_version(
        document_id=document_id,
        html_content=html_content,
        user_prompt="",
        edit_summary="Manual edit",
        model_used="manual",
        tokens_used=0,
    )
```

### Step 5.2: Backend — Add Manual Edit Endpoint

**File:** `backend/app/api/sessions.py`

Add import at top (if not present):
```python
from pydantic import BaseModel, Field
```

Add request model (near other models):
```python
class ManualEditRequest(BaseModel):
    html_content: str = Field(..., min_length=1)
```

Add endpoint:
```python
@router.post("/api/documents/{document_id}/manual-edit")
async def save_manual_edit(document_id: str, body: ManualEditRequest):
    """Save manual HTML edits as a new version."""
    from app.services.session_service import session_service

    version = await session_service.save_manual_edit(
        document_id, body.html_content
    )
    return {"version": version, "success": True}
```

### Step 5.3: Backend — Add Tests

**New file:** `backend/tests/test_manual_edit.py`

```python
"""Tests for manual HTML editing endpoint."""
import os
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import init_db


@pytest.fixture
async def client():
    await init_db(":memory:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def setup_doc(client: AsyncClient):
    """Create session + document + initial version."""
    resp = await client.post("/api/sessions")
    sid = resp.json()["session_id"]
    session = await client.get(f"/api/sessions/{sid}")
    doc_id = session.json()["documents"][0]["id"]
    return sid, doc_id


async def test_manual_edit_creates_version(client: AsyncClient, setup_doc):
    _, doc_id = setup_doc
    resp = await client.post(
        f"/api/documents/{doc_id}/manual-edit",
        json={"html_content": "<h1>Manually Edited</h1>"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["version"] >= 1

    # Verify version details
    versions_resp = await client.get(f"/api/documents/{doc_id}/versions")
    versions = versions_resp.json()["versions"]
    latest = max(versions, key=lambda v: v["version"])
    assert latest["model_used"] == "manual"
    assert latest["edit_summary"] == "Manual edit"


async def test_manual_edit_empty_content_rejected(client: AsyncClient, setup_doc):
    _, doc_id = setup_doc
    resp = await client.post(
        f"/api/documents/{doc_id}/manual-edit",
        json={"html_content": ""},
    )
    assert resp.status_code == 422


async def test_manual_edit_missing_content_rejected(client: AsyncClient, setup_doc):
    _, doc_id = setup_doc
    resp = await client.post(
        f"/api/documents/{doc_id}/manual-edit",
        json={},
    )
    assert resp.status_code == 422
```

### Step 5.4: Frontend — Add `saveManualEdit` API Method

**File:** `frontend/src/services/api.ts`

Add method to the `api` object:
```typescript
async saveManualEdit(documentId: string, htmlContent: string): Promise<{ version: number; success: boolean }> {
  const resp = await fetch(`/api/documents/${documentId}/manual-edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html_content: htmlContent }),
  });
  if (!resp.ok) throw new Error(`Save failed: ${resp.status}`);
  return resp.json();
},
```

### Step 5.5: Frontend — Make CodeMirrorViewer Configurable

**File:** `frontend/src/components/CodeViewer/CodeMirrorViewer.tsx`

Replace the entire file:
```typescript
import { useEffect, useRef } from 'react';
import { basicSetup } from 'codemirror';
import { EditorView } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { html } from '@codemirror/lang-html';
import { oneDark } from '@codemirror/theme-one-dark';

interface CodeMirrorViewerProps {
  code: string;
  onContentChange?: (newCode: string) => void;
  disabled?: boolean;
}

const themeCompartment = new Compartment();
const editableCompartment = new Compartment();
const readOnlyCompartment = new Compartment();

function getThemeExtension() {
  const attr = document.documentElement.getAttribute('data-theme');
  return attr === 'light' ? [] : oneDark;
}

export default function CodeMirrorViewer({ code, onContentChange, disabled = true }: CodeMirrorViewerProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onContentChangeRef = useRef(onContentChange);

  // Keep callback ref current
  useEffect(() => {
    onContentChangeRef.current = onContentChange;
  }, [onContentChange]);

  // Create editor once on mount
  useEffect(() => {
    if (!editorRef.current) return;

    const state = EditorState.create({
      doc: code,
      extensions: [
        basicSetup,
        html(),
        themeCompartment.of(getThemeExtension()),
        editableCompartment.of(EditorView.editable.of(!disabled)),
        readOnlyCompartment.of(EditorState.readOnly.of(disabled)),
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (update.docChanged && onContentChangeRef.current) {
            onContentChangeRef.current(update.state.doc.toString());
          }
        }),
      ],
    });

    viewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    // Listen for theme attribute changes via MutationObserver
    const observer = new MutationObserver(() => {
      viewRef.current?.dispatch({
        effects: themeCompartment.reconfigure(getThemeExtension()),
      });
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    return () => {
      observer.disconnect();
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update editable/readOnly when disabled prop changes
  useEffect(() => {
    if (!viewRef.current) return;
    viewRef.current.dispatch({
      effects: [
        editableCompartment.reconfigure(EditorView.editable.of(!disabled)),
        readOnlyCompartment.reconfigure(EditorState.readOnly.of(disabled)),
      ],
    });
  }, [disabled]);

  // Update document when code changes externally
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

### Step 5.6: Frontend — Add Edit Mode to CodeView

**File:** `frontend/src/components/CodeViewer/CodeView.tsx`

Replace the entire file:
```typescript
import { useState, useEffect, useCallback } from 'react';
import CodeMirrorViewer from './CodeMirrorViewer';
import CopyButton from './CopyButton';
import { api } from '../../services/api';
import './CodeView.css';

interface CodeViewProps {
  html: string;
  documentId?: string | null;
  onSaved?: () => void;
  isStreaming?: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}

export default function CodeView({ html, documentId, onSaved, isStreaming, onDirtyChange }: CodeViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedHtml, setEditedHtml] = useState(html);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Reset when html prop changes (AI update or document switch)
  useEffect(() => {
    setEditedHtml(html);
    setIsDirty(false);
    setIsEditing(false);
    setSaveError(null);
  }, [html]);

  // Notify parent of dirty state changes
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  const handleContentChange = useCallback((newCode: string) => {
    setEditedHtml(newCode);
    setIsDirty(newCode !== html);
  }, [html]);

  const handleToggleEdit = useCallback(() => {
    if (isEditing && isDirty) {
      // Exiting edit mode with unsaved changes — discard
      setEditedHtml(html);
      setIsDirty(false);
    }
    setIsEditing(prev => !prev);
    setSaveError(null);
  }, [isEditing, isDirty, html]);

  const handleSave = useCallback(async () => {
    if (!documentId || !isDirty) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await api.saveManualEdit(documentId, editedHtml);
      setIsDirty(false);
      setIsEditing(false);
      onSaved?.();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  }, [documentId, isDirty, editedHtml, onSaved]);

  const handleDiscard = useCallback(() => {
    setEditedHtml(html);
    setIsDirty(false);
    setSaveError(null);
  }, [html]);

  return (
    <div className="code-view-container">
      <div className="code-view-header">
        <span className="code-view-title">
          HTML Source
          {isDirty && <span className="dirty-indicator">*</span>}
        </span>
        <div className="code-view-actions">
          {isDirty && isEditing && (
            <>
              <button
                className="code-discard-btn"
                onClick={handleDiscard}
                disabled={isSaving}
                type="button"
              >
                Discard
              </button>
              <button
                className="code-save-btn"
                onClick={handleSave}
                disabled={isSaving}
                type="button"
              >
                {isSaving ? 'Saving...' : 'Save Version'}
              </button>
            </>
          )}
          <button
            className={`edit-toggle-btn${isEditing ? ' active' : ''}`}
            onClick={handleToggleEdit}
            disabled={isStreaming}
            title={isEditing ? 'Exit edit mode' : 'Edit HTML'}
            type="button"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
          </button>
          <CopyButton text={isEditing ? editedHtml : html} label="Copy Code" />
        </div>
      </div>
      {saveError && (
        <div className="code-save-error">
          {saveError}
          <button type="button" onClick={() => setSaveError(null)}>×</button>
        </div>
      )}
      <div className="code-view-body">
        <CodeMirrorViewer
          code={isEditing ? editedHtml : html}
          onContentChange={isEditing ? handleContentChange : undefined}
          disabled={!isEditing}
        />
      </div>
    </div>
  );
}
```

### Step 5.7: Add Edit Mode CSS

**File:** `frontend/src/components/CodeViewer/CodeView.css`

Add at end (or replace relevant sections):
```css
/* --- Code View Actions Bar --- */
.code-view-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* --- Edit Toggle Button --- */
.edit-toggle-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  padding: 0.375rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.edit-toggle-btn:hover:not(:disabled) {
  background: var(--surface-highlight);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.edit-toggle-btn.active {
  background: var(--accent-primary-muted);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.edit-toggle-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* --- Dirty Indicator --- */
.dirty-indicator {
  margin-left: 0.25rem;
  color: var(--signal-warning);
  font-family: var(--font-mono);
  font-weight: var(--fw-bold);
}

/* --- Save / Discard Buttons --- */
.code-save-btn {
  background: var(--gradient-send-btn);
  color: var(--text-inverse);
  border: none;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  transition: all var(--duration-fast) var(--ease-out-expo);
  box-shadow: var(--shadow-sm);
}

.code-save-btn:hover:not(:disabled) {
  background: var(--gradient-send-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.code-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.code-discard-btn {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.code-discard-btn:hover:not(:disabled) {
  background: var(--surface-highlight);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.code-discard-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* --- Save Error Banner --- */
.code-save-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--signal-error-muted);
  color: var(--signal-error);
  padding: 0.5rem 1rem;
  border-left: 3px solid var(--signal-error);
  font-family: var(--font-body);
  font-size: var(--fs-sm);
}

.code-save-error button {
  background: none;
  border: none;
  color: var(--signal-error);
  cursor: pointer;
  font-size: var(--fs-md);
  padding: 0 0.25rem;
  opacity: 0.7;
  transition: opacity var(--duration-fast);
}

.code-save-error button:hover {
  opacity: 1;
}
```

### Step 5.8: Wire CodeView Props in App.tsx

**File:** `frontend/src/App.tsx`

Add state for dirty tracking:
```typescript
const [isCodeViewDirty, setIsCodeViewDirty] = useState(false);
```

Update `handleSendMessage` to block while dirty:
```typescript
const handleSendMessage = useCallback((message: string, _files?: File[], templateName?: string, userContent?: string) => {
  if (isCodeViewDirty) {
    setError('Save or discard your HTML changes before sending a message.');
    return;
  }
  if (message.trim()) {
    setError(null)
    sendMessage(message, activeDocument?.id, templateName, userContent)
  }
}, [sendMessage, activeDocument, isCodeViewDirty])
```

In `HtmlViewer`, add new props to the component's type signature:
```typescript
onDirtyChange?: (dirty: boolean) => void;
```

Update `CodeView` usage inside `HtmlViewer`:
```typescript
<CodeView
  html={displayHtml}
  documentId={activeDocumentId}
  onSaved={async () => {
    onVersionRefresh?.();
  }}
  isStreaming={isStreaming}
  onDirtyChange={onDirtyChange}
/>
```

**NOTE:** The `onSaved` callback should trigger `refreshDocuments()` and reopen version history if open. Pass the callback from `ChatApp` through `HtmlViewer`:

In `ChatApp`, add a save handler:
```typescript
const handleCodeViewSaved = useCallback(async () => {
  await refreshDocuments();
  if (historyOpen) {
    setHistoryOpen(false);
    setTimeout(() => setHistoryOpen(true), 50);
  }
}, [refreshDocuments, historyOpen]);
```

Pass it through:
```typescript
<HtmlViewer
  // ... existing props ...
  onCodeViewSaved={handleCodeViewSaved}
  onDirtyChange={setIsCodeViewDirty}
/>
```

In `HtmlViewer`, wire to CodeView:
```typescript
<CodeView
  html={displayHtml}
  documentId={activeDocumentId}
  onSaved={onCodeViewSaved}
  isStreaming={isStreaming}
  onDirtyChange={onDirtyChange}
/>
```

### Phase 5 Verification

```bash
cd backend && python -m pytest -v        # All tests pass including new manual edit tests
cd backend && ruff check backend/        # Lint clean
cd backend && mypy backend/              # Type check clean
cd frontend && npm run build             # TypeScript + Vite clean
cd frontend && npm run lint              # ESLint clean
```

Manual test:
1. Switch to Code view → pencil icon visible next to Copy button
2. Click pencil → editor becomes writable, pencil highlights with accent color
3. Type a change → `*` appears next to "HTML Source", Save/Discard buttons appear
4. Click Discard → changes revert, buttons disappear
5. Make edit again → click Save → "Saving..." → new version in history
6. Try sending chat while dirty → error banner: "Save or discard your HTML changes..."
7. During streaming → pencil icon disabled (can't enter edit mode)
8. AI sends update → editor resets, edit mode exits

---

## Phase 6: Polish (Items 3a, 3c)

### Step 6.1: Pencil Icon on Tab Hover (3a)

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.tsx`

Inside the tab button, after the title span but before the close button, add a rename icon:
```typescript
{editingId !== doc.id && onRenameDocument && (
  <span
    className="tab-rename-icon"
    role="button"
    tabIndex={0}
    onClick={(e) => {
      e.stopPropagation();
      handleDoubleClick(doc);
    }}
    onKeyDown={(e) => {
      if (e.key === 'Enter') {
        e.stopPropagation();
        handleDoubleClick(doc);
      }
    }}
    title="Rename document"
  >
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
    </svg>
  </span>
)}
```

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.css`

Add:
```css
/* --- Tab Rename Icon --- */
.tab-rename-icon {
  display: flex;
  align-items: center;
  padding: 0.125rem;
  color: var(--text-tertiary);
  opacity: 0;
  cursor: pointer;
  transition: opacity var(--duration-fast), color var(--duration-fast);
  flex-shrink: 0;
}

.document-tab:hover .tab-rename-icon {
  opacity: 0.5;
}

.tab-rename-icon:hover {
  opacity: 1 !important;
  color: var(--accent-primary);
}
```

### Step 6.2: Document Name Badge on Messages (3c)

Only shown when `documents.length > 1`.

**File:** `frontend/src/components/ChatWindow/index.tsx`

Add new props:
```typescript
interface ChatWindowProps {
  // ... existing ...
  documents?: Document[];  // NEW
}
```

Pass to MessageList:
```typescript
<MessageList
  messages={messages}
  isStreaming={isStreaming}
  streamingContent={streamingContent}
  onSelectTemplate={handleSelectTemplate}
  documents={documents || []}
/>
```

Add import for Document type if not present.

**File:** `frontend/src/components/ChatWindow/MessageList.tsx`

Add to imports:
```typescript
import type { ChatMessage, Document } from '../../types';
```

Update props:
```typescript
interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamingContent?: string;
  onSelectTemplate?: (prompt: string) => void;
  documents?: Document[];  // NEW
}
```

Add destructuring:
```typescript
const MessageList: React.FC<MessageListProps> = ({
  // ... existing ...
  documents = [],
}) => {
```

Add doc name lookup helper inside component:
```typescript
const docNameMap = documents.length > 1
  ? new Map(documents.map(d => [d.id, d.title]))
  : null;
```

In the message rendering, add doc badge after the timestamp:
```typescript
<div className="message-header">
  <span className="message-sender">
    {message.role === 'user' ? 'You' : 'ARCHITECT'}
  </span>
  <span className="message-meta">
    {docNameMap && message.document_id && docNameMap.has(message.document_id) && (
      <span className="message-doc-badge">{docNameMap.get(message.document_id)}</span>
    )}
    <span className="message-timestamp">
      {formatTimestamp(message.created_at)}
    </span>
  </span>
</div>
```

**File:** `frontend/src/components/ChatWindow/MessageList.css`

Add:
```css
/* --- Message Meta (timestamp + doc badge) --- */
.message-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.message-doc-badge {
  display: inline-block;
  background: var(--surface-highlight);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

**File:** `frontend/src/App.tsx`

Pass documents to ChatWindow:
```typescript
<ChatWindow
  // ... existing props ...
  documents={documents}
/>
```

### Phase 6 Verification

```bash
cd frontend && npm run build
cd frontend && npm run lint
```

Manual test:
1. Hover over a document tab → small pencil icon fades in
2. Click pencil → enters rename mode (same as double-click)
3. Move mouse away → pencil fades out
4. Create 2 documents → verify messages show doc name badges
5. With single document → verify NO doc badges shown

---

## Files Changed Summary

### New files (3):
| File | Purpose |
|------|---------|
| `frontend/src/components/ConfirmDialog/ConfirmDialog.tsx` | Reusable themed confirm dialog |
| `frontend/src/components/ConfirmDialog/ConfirmDialog.css` | Dialog styles |
| `backend/tests/test_manual_edit.py` | Tests for manual edit endpoint |

### Modified files (~19):
| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | activeDocument.id, dirty guard, loading state, new session, doc badges |
| `frontend/src/App.css` | Loading screen styles |
| `frontend/src/hooks/useSSEChat.ts` | sendingRef, startNewSession, isInitializing, templateName |
| `frontend/src/types/index.ts` | templateName + userContent on ChatMessage |
| `frontend/src/services/api.ts` | saveManualEdit method |
| `frontend/src/components/ChatWindow/index.tsx` | Three-dot menu, new props, documents passthrough |
| `frontend/src/components/ChatWindow/ChatWindow.css` | Menu styles |
| `frontend/src/components/ChatWindow/ChatInput.tsx` | Template badge system + inline TemplatePopover component |
| `frontend/src/components/ChatWindow/ChatInput.css` | Badge + popover styles |
| `frontend/src/components/ChatWindow/MessageList.tsx` | Template display, doc badges |
| `frontend/src/components/ChatWindow/MessageList.css` | Badge + meta styles |
| `frontend/src/components/CodeViewer/CodeMirrorViewer.tsx` | Editable mode with compartments |
| `frontend/src/components/CodeViewer/CodeView.tsx` | Edit toggle, save/discard, dirty tracking |
| `frontend/src/components/CodeViewer/CodeView.css` | Edit mode styles |
| `frontend/src/components/DocumentTabs/DocumentTabs.tsx` | Pencil icon, ConfirmDialog |
| `frontend/src/components/DocumentTabs/DocumentTabs.css` | Pencil hover styles |
| `frontend/src/components/VersionHistory/VersionTimeline.tsx` | ConfirmDialog with educational message |
| `backend/app/services/session_service.py` | save_manual_edit method |
| `backend/app/api/sessions.py` | Manual edit endpoint + model |

### Skipped items (from original plan):
| Item | Reason |
|------|--------|
| 2a — New Document button | Chat-driven creation is more intuitive (user decision) |
| 3d — Keyboard shortcuts | UI should be intuitive without them (user decision) |

---

## Deferred (Future Plans)

| Feature | Why Deferred | Effort |
|---------|-------------|--------|
| Visual diff between versions | Needs diff library (diff2html) | 2-3 days |
| Click-to-edit on preview | Needs iframe `postMessage` bridge | 3-5 days |
| Collaborative editing awareness | Needs WebSocket/polling | 5+ days |
| Smart template tags (compose mode) | Evolution of badge system (Approach 1) | 2-3 days |
| Toast notification system | Useful for save confirmations, undo actions | 1-2 days |
| Template preview thumbnails | Pre-rendered screenshots or SVG | 2 days |
| Responsive/mobile design | SplitPane on mobile | 1-2 days |

---

## Final Verification (After All Phases)

```bash
# Backend
cd backend && python -m pytest -v              # All tests pass (245+ expected)
cd backend && ruff check backend/              # Lint clean
cd backend && mypy backend/                    # Type check clean

# Frontend
cd frontend && npm run build                   # TypeScript + Vite clean
cd frontend && npm run lint                    # ESLint clean
```

Expected test count: 245+ (existing 244 + new manual edit tests minus 1 pre-existing failure `test_init_db_creates_file`).

---

## Post-Implementation

After all phases pass verification:
1. Update `IMPLEMENTATION_PLANS/013_UX_IMPROVEMENTS.md` status to `COMPLETE`
2. Update `CLAUDE.md` plan table: `013 | UX Improvements | COMPLETE`
3. Update `IMPLEMENTATION_PLANS/README.md` if applicable
