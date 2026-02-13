# Implementation Plan 009a: Visual Foundation ("Obsidian Terminal")

## Status: COMPLETE

All 6 phases implemented and verified (February 2026):
- 14 CSS files replaced (zero hardcoded colors, zero `prefers-color-scheme`, zero system fonts)
- 2 new files created (`theme.css`, `ThemeToggle.tsx`)
- 6 TSX files modified (`index.html`, `main.tsx`, `App.tsx`, `SplitPane.tsx`, `ChatWindow/index.tsx`, `MessageList.tsx`)
- TypeScript clean, Vite build clean, ESLint clean
- Theme: dark-first via CSS custom properties, light mode via `[data-theme="light"]`
- Fonts: Bricolage Grotesque (display), IBM Plex Sans (body), JetBrains Mono (mono) via Google Fonts
- Known issue (deferred to 009b): `CodeMirrorViewer.tsx` `matchMedia` usage — **RESOLVED in Plan 009b** (replaced with `MutationObserver` on `data-theme` attribute)

---

## STOP - READ THIS FIRST

**DO NOT START** this implementation until:
- Plan 001 (Backend Foundation) is FULLY complete and tested
- Plan 002 (Surgical Editing Engine) is FULLY complete and tested
- Plan 003 (Multi-Model Routing) is FULLY complete and tested
- Plan 004 (Frontend Enhancements) is FULLY complete and tested
- Plan 005 (Export Pipeline) is FULLY complete and tested
- Plan 006 (File Upload & Templates) is FULLY complete and tested
- Plan 007 (Template Optimization) is FULLY complete and tested
- You have read this ENTIRE document
- You understand that this plan touches ONLY frontend CSS and minimal TSX wiring
- You understand that Plan 009 (existing) will be renamed to 009b and depends on THIS plan

**DESTRUCTIVE ACTIONS PROHIBITED:**
- Do NOT modify any backend files (no Python, no API endpoints, no system prompts, no routing logic, no SSE streaming)
- Do NOT add new npm dependencies (no Tailwind, no styled-components, no motion libraries)
- Do NOT modify `useSSEChat.ts` or any service files (`api.ts`, `templateService.ts`, `uploadService.ts`)
- Do NOT break existing functionality - every feature must work identically after reskin
- Do NOT use `@media (prefers-color-scheme: dark)` anywhere - use `[data-theme="light"]` overrides ONLY
- Do NOT commit until ALL phases pass TypeScript, Vite build, and ESLint checks

**DEPENDENCIES:**
- Plans 001-007: Complete backend and frontend infrastructure
- Google Fonts CDN: Bricolage Grotesque, IBM Plex Sans, JetBrains Mono

**ESTIMATED EFFORT:** 2-3 days

---

## Context & Rationale

### Current State
The frontend was rebuilt during Plans 001-007 with focus on functionality. The visual layer uses:
- **System fonts** (Segoe UI, Roboto, Arial) - explicitly forbidden by project aesthetic guidelines in CLAUDE.md
- **~40 `@media (prefers-color-scheme: dark)` blocks** scattered across 14 CSS files with hardcoded colors
- **No CSS custom properties** - every color is a magic hex value
- **Minimal animations** - just fade/slide modals, typing dots, blink cursor
- **Generic UI** - standard chat bubbles, colored pill status indicators, 3-dot divider
- **No theme toggle** - relies entirely on OS preference

### Design Concept: "Obsidian Terminal"
Dark-mode-first theme where generating HTML feels like "summoning structured intelligence from a futuristic system." Light mode ("Ink on Parchment") available via manual toggle.

### Design Decisions
- **Default theme**: Dark mode, manual toggle to light
- **AI persona label**: "ARCHITECT" (replaces "AI Assistant")
- **Template icons**: Keep existing emojis (not monospace codes)
- **Dependencies**: Zero new npm packages

### What Changes
- **14 CSS files**: Complete rewrite to use CSS custom properties, remove all `@media (prefers-color-scheme: dark)` blocks
- **1 new CSS file**: `theme.css` with all custom properties and keyframe animations
- **1 new TSX file**: `ThemeToggle.tsx` for sun/moon toggle
- **4 TSX files modified**: `index.html` (fonts), `main.tsx` (import order), `App.tsx` (prop wiring), `SplitPane.tsx` (divider redesign), `ChatWindow/index.tsx` (ThemeToggle + status), `MessageList.tsx` ("ARCHITECT" label)

### Files Inventory

**14 CSS files (all rewritten):**
1. `frontend/src/index.css` (33 lines)
2. `frontend/src/App.css` (541 lines)
3. `frontend/src/components/Layout/SplitPane.css` (155 lines)
4. `frontend/src/components/ChatWindow/ChatWindow.css` (156 lines)
5. `frontend/src/components/ChatWindow/ChatInput.css` (507 lines)
6. `frontend/src/components/ChatWindow/MessageList.css` (203 lines)
7. `frontend/src/components/ChatWindow/PromptLibraryModal.css` (472 lines)
8. `frontend/src/components/ChatWindow/PromptLibraryButton.css` (68 lines)
9. `frontend/src/components/Chat/StreamingMarkdown.css` (201 lines)
10. `frontend/src/components/CodeViewer/CodeView.css` (73 lines)
11. `frontend/src/components/DocumentTabs/DocumentTabs.css` (89 lines)
12. `frontend/src/components/VersionHistory/VersionTimeline.css` (268 lines)
13. `frontend/src/components/EmptyState/TemplateCards.css` (141 lines)
14. `frontend/src/components/Export/ExportDropdown.css` (93 lines)

**New files:**
- `frontend/src/theme.css`
- `frontend/src/components/ThemeToggle.tsx`

**Modified TSX files:**
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout/SplitPane.tsx`
- `frontend/src/components/ChatWindow/index.tsx`
- `frontend/src/components/ChatWindow/MessageList.tsx`

---

## Strict Rules - Check Before Each Phase

### CSS Architecture Rules
- [ ] ALL colors use CSS custom properties from `theme.css` - zero hardcoded hex/rgb values in component CSS
- [ ] NO `@media (prefers-color-scheme: dark)` anywhere - use `[data-theme="light"]` overrides ONLY
- [ ] ALL fonts use `var(--font-display)`, `var(--font-body)`, or `var(--font-mono)` - zero font-family strings in component CSS
- [ ] ALL border-radius values use `var(--radius-*)` tokens
- [ ] ALL shadows use `var(--shadow-*)` tokens
- [ ] ALL transitions use `var(--duration-*)` and `var(--ease-*)` tokens

### Quality Rules
- [ ] TypeScript clean: `npx tsc --noEmit` passes with zero errors
- [ ] Vite build clean: `npm run build` passes with zero errors
- [ ] ESLint clean: `npm run lint` passes with zero errors
- [ ] Every existing button, input, modal, and interactive element still functions
- [ ] Scrolling works in all scrollable areas (message list, version timeline, code view)
- [ ] Responsive breakpoints preserved (768px, 480px)

### Theme Rules
- [ ] Dark mode is default (no `data-theme` attribute = dark)
- [ ] Light mode activated by `data-theme="light"` on `<html>`
- [ ] Theme persists in `localStorage` key `ai-html-builder-theme`
- [ ] Theme initializes before React hydration (script in `<head>`)
- [ ] Both themes have sufficient contrast ratios for accessibility

---

## Phase 0: Theme Foundation

### Objective
Create the CSS custom properties file, load Google Fonts, set up theme initialization, and create the ThemeToggle component.

### 0.1 Create `frontend/src/theme.css`

This file defines ALL design tokens as CSS custom properties. Dark mode is the default (`:root`). Light mode overrides use `[data-theme="light"]`. All keyframe animations live here.

**File:** `frontend/src/theme.css`

```css
/* ==========================================================================
   AI HTML Builder - Theme System ("Obsidian Terminal")
   Dark mode = default (:root). Light mode = [data-theme="light"] overrides.
   All component CSS references these tokens exclusively.
   ========================================================================== */

/* --- Typography Tokens --- */
:root {
  --font-display: 'Bricolage Grotesque', system-ui, sans-serif;
  --font-body: 'IBM Plex Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --fw-thin: 200;
  --fw-light: 300;
  --fw-regular: 400;
  --fw-medium: 500;
  --fw-bold: 700;
  --fw-heavy: 800;

  --fs-xs: 0.6875rem;
  --fs-sm: 0.75rem;
  --fs-base: 0.875rem;
  --fs-md: 1rem;
  --fs-lg: 1.25rem;
  --fs-xl: 1.75rem;
  --fs-display: 2.5rem;

  --leading-tight: 1.2;
  --leading-normal: 1.5;
  --leading-relaxed: 1.7;

  --tracking-tight: -0.02em;
  --tracking-normal: 0;
  --tracking-wide: 0.08em;
  --tracking-widest: 0.15em;
}

/* --- Dark Mode (Default) --- */
:root {
  --surface-void: #08090A;
  --surface-base: #0D0F12;
  --surface-raised: #141720;
  --surface-overlay: #1A1E2A;
  --surface-highlight: #232838;

  --border-subtle: #1E2234;
  --border-default: #2A2F42;
  --border-strong: #3D4460;
  --border-accent: #4F6AFF;

  --text-primary: #E8ECF4;
  --text-secondary: #8B93A8;
  --text-tertiary: #555E75;
  --text-inverse: #0D0F12;

  --accent-primary: #4F6AFF;
  --accent-primary-hover: #6B82FF;
  --accent-primary-muted: rgba(79, 106, 255, 0.12);
  --accent-primary-glow: rgba(79, 106, 255, 0.35);

  --signal-active: #00E5CC;
  --signal-active-glow: rgba(0, 229, 204, 0.25);
  --signal-active-muted: rgba(0, 229, 204, 0.08);

  --signal-warning: #FFB020;
  --signal-warning-muted: rgba(255, 176, 32, 0.10);

  --signal-error: #FF4D6A;
  --signal-error-muted: rgba(255, 77, 106, 0.10);

  --signal-success: #34D399;
  --signal-success-muted: rgba(52, 211, 153, 0.10);

  --gradient-header: linear-gradient(135deg, #0D0F12 0%, #141720 50%, #1A1E2A 100%);
  --gradient-send-btn: linear-gradient(135deg, #4F6AFF 0%, #7B5AFF 100%);
  --gradient-send-hover: linear-gradient(135deg, #6B82FF 0%, #9575FF 100%);
  --gradient-user-msg: linear-gradient(135deg, #1A1E56 0%, #1E1240 100%);
  --gradient-ai-glow: linear-gradient(135deg, rgba(0, 229, 204, 0.03) 0%, rgba(79, 106, 255, 0.03) 100%);

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.6);
  --shadow-glow-accent: 0 0 20px rgba(79, 106, 255, 0.15);
  --shadow-glow-signal: 0 0 20px rgba(0, 229, 204, 0.15);

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 500ms;
  --duration-dramatic: 800ms;
}

/* --- Light Mode ("Ink on Parchment") --- */
[data-theme="light"] {
  --surface-void: #F0EDE8;
  --surface-base: #F7F5F2;
  --surface-raised: #FFFFFF;
  --surface-overlay: #FFFFFF;
  --surface-highlight: #EDE9E3;

  --border-subtle: #E5E0D8;
  --border-default: #D4CFC5;
  --border-strong: #B8B0A4;
  --border-accent: #3D50CC;

  --text-primary: #1A1A2E;
  --text-secondary: #6B6880;
  --text-tertiary: #A09DB0;
  --text-inverse: #F7F5F2;

  --accent-primary: #3D50CC;
  --accent-primary-hover: #2E3EAA;
  --accent-primary-muted: rgba(61, 80, 204, 0.08);
  --accent-primary-glow: rgba(61, 80, 204, 0.20);

  --signal-active: #0D9488;
  --signal-active-glow: rgba(13, 148, 136, 0.15);
  --signal-active-muted: rgba(13, 148, 136, 0.06);

  --signal-warning: #D97706;
  --signal-warning-muted: rgba(217, 119, 6, 0.08);

  --signal-error: #DC2626;
  --signal-error-muted: rgba(220, 38, 38, 0.08);

  --signal-success: #059669;
  --signal-success-muted: rgba(5, 150, 105, 0.08);

  --gradient-header: linear-gradient(135deg, #F7F5F2 0%, #FFFFFF 100%);
  --gradient-send-btn: linear-gradient(135deg, #3D50CC 0%, #5B3DBB 100%);
  --gradient-send-hover: linear-gradient(135deg, #2E3EAA 0%, #4A2FA8 100%);
  --gradient-user-msg: linear-gradient(135deg, #E8EDFF 0%, #F0EBFF 100%);
  --gradient-ai-glow: linear-gradient(135deg, rgba(13, 148, 136, 0.03) 0%, rgba(61, 80, 204, 0.03) 100%);

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.12);
  --shadow-glow-accent: 0 0 20px rgba(61, 80, 204, 0.10);
  --shadow-glow-signal: 0 0 20px rgba(13, 148, 136, 0.10);
}

/* ==========================================================================
   Keyframe Animations
   ========================================================================== */

@keyframes summon-pulse {
  0%   { box-shadow: 0 0 0 0 var(--accent-primary-glow); transform: scale(1); }
  15%  { transform: scale(0.88); }
  40%  { box-shadow: 0 0 0 12px var(--accent-primary-glow); transform: scale(1.12); }
  100% { box-shadow: 0 0 0 40px transparent; transform: scale(1); }
}

@keyframes conduit-sweep {
  0%   { background-position: 50% -100%; }
  100% { background-position: 50% 200%; }
}

@keyframes conduit-pulse {
  0%, 100% { opacity: 0.4; height: 40%; }
  50%      { opacity: 1; height: 70%; }
}

@keyframes status-beacon {
  0%, 100% { box-shadow: 0 0 4px var(--signal-active); opacity: 1; }
  50%      { box-shadow: 0 0 16px var(--signal-active-glow); opacity: 0.6; }
}

@keyframes progress-sweep {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes materialize {
  0%   { opacity: 0; clip-path: inset(0 0 100% 0); }
  60%  { opacity: 1; clip-path: inset(0 0 20% 0); }
  100% { opacity: 1; clip-path: inset(0 0 0% 0); }
}

@keyframes completion-glow {
  0%   { box-shadow: inset 0 0 0 1px var(--signal-active), 0 0 30px var(--signal-active-glow); }
  100% { box-shadow: inset 0 0 0 1px transparent, 0 0 0 transparent; }
}

@keyframes cursor-blink {
  0%, 50%  { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fade-left {
  from { opacity: 0; transform: translateX(-8px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes modal-enter {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes card-enter {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes dropdown-enter {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fade-pulse {
  0%, 100% { opacity: 0.6; }
  50%      { opacity: 1; }
}

@keyframes border-stream {
  0%, 100% { border-left-color: var(--accent-primary); }
  50%      { border-left-color: var(--signal-active); }
}
```

### 0.2 Update `frontend/index.html`

Add Google Fonts preconnect and stylesheet links. Add theme initialization script in `<head>` to prevent flash of wrong theme.

**File:** `frontend/index.html` (COMPLETE REPLACEMENT)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI HTML Builder</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200;12..96,800&family=IBM+Plex+Sans:wght@300;400;500&family=JetBrains+Mono:wght@300;400;700&display=swap" rel="stylesheet" />
    <script>
      const t = localStorage.getItem('ai-html-builder-theme');
      if (t === 'light') document.documentElement.dataset.theme = 'light';
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### 0.3 Update `frontend/src/main.tsx`

Import `theme.css` BEFORE `index.css` so custom properties are available to all subsequent styles.

**File:** `frontend/src/main.tsx` (COMPLETE REPLACEMENT)

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### 0.4 Create `frontend/src/components/ThemeToggle.tsx`

Inline SVG sun/moon toggle. No dependencies. Reads/writes `localStorage` and `data-theme` attribute.

**File:** `frontend/src/components/ThemeToggle.tsx` (NEW FILE)

```typescript
import { useState, useCallback } from 'react';

type Theme = 'dark' | 'light';
const STORAGE_KEY = 'ai-html-builder-theme';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(STORAGE_KEY) as Theme) || 'dark'
  );

  const toggle = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (next === 'light') {
      document.documentElement.dataset.theme = 'light';
    } else {
      delete document.documentElement.dataset.theme;
    }
    localStorage.setItem(STORAGE_KEY, next);
  }, [theme]);

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      type="button"
    >
      {theme === 'dark' ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  );
}
```

### 0.5 Rewrite `frontend/src/index.css`

Replace hardcoded colors and fonts with CSS custom properties. Add themed scrollbar and selection styles. Add `.theme-toggle` button styles.

**File:** `frontend/src/index.css` (COMPLETE REPLACEMENT)

```css
/* Global Reset & Base */
* {
  box-sizing: border-box;
}

:root {
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: var(--font-body);
  font-weight: var(--fw-regular);
  font-size: var(--fs-base);
  line-height: var(--leading-normal);
  background: var(--surface-base);
  color: var(--text-primary);
}

#root {
  height: 100vh;
  width: 100vw;
}

/* Scrollbar Styling */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--border-strong) transparent;
}

*::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

*::-webkit-scrollbar-track {
  background: transparent;
}

*::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 3px;
}

*::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

/* Selection */
::selection {
  background: var(--accent-primary-muted);
  color: var(--text-primary);
}

/* Focus Visible */
:focus-visible {
  outline: 2px solid var(--border-accent);
  outline-offset: 2px;
}

/* Theme Toggle Button (used globally) */
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface-highlight);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.theme-toggle:hover {
  color: var(--text-primary);
  border-color: var(--border-accent);
  background: var(--accent-primary-muted);
}
```

### Phase 0 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] App loads with dark theme by default
- [ ] No flash of light content on page load
- [ ] Google Fonts load (check Network tab for `fonts.googleapis.com`)
- [ ] ThemeToggle component renders (will be wired in Phase 1)

---

## Phase 1: Core Layout (App.css + SplitPane)

### Objective
Rewrite `App.css` and `SplitPane.css` to use CSS variables. Update `SplitPane.tsx` to accept `isProcessing` prop and replace 3-dot divider with energy line. Update `App.tsx` to pass streaming state through.

### 1.1 Rewrite `frontend/src/App.css`

Remove ALL `@media (prefers-color-scheme: dark)` blocks. Replace all hardcoded colors with CSS custom properties.

**File:** `frontend/src/App.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   App Layout
   ========================================================================== */

.App {
  height: 100vh;
  overflow: hidden;
  background: var(--surface-void);
}

/* ==========================================================================
   Chat Window (layout shell - detailed styles in ChatWindow.css)
   ========================================================================== */

.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-base);
  border-right: 1px solid var(--border-subtle);
}

/* --- Chat Header --- */
.chat-header {
  background: var(--gradient-header);
  color: var(--text-primary);
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-default);
}

.chat-header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: var(--fw-thin);
  font-size: var(--fs-lg);
  letter-spacing: var(--tracking-tight);
  color: var(--text-primary);
}

.session-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* --- Status Indicator (Monospace Diagnostic) --- */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-regular);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  border: 1px solid var(--border-subtle);
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.status-indicator.ready {
  background: var(--signal-active-muted);
  color: var(--signal-active);
  border-color: rgba(0, 229, 204, 0.15);
}

.status-indicator.processing {
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
  border-color: rgba(79, 106, 255, 0.2);
  animation: fade-pulse 2s ease-in-out infinite;
}

/* --- Error Banner --- */
.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--signal-error-muted);
  color: var(--signal-error);
  padding: 0.75rem 1.5rem;
  border-left: 3px solid var(--signal-error);
  font-size: var(--fs-base);
}

.error-banner .error-dismiss {
  background: none;
  border: none;
  color: var(--signal-error);
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0 0.25rem;
  opacity: 0.7;
  transition: opacity var(--duration-fast);
}

.error-banner .error-dismiss:hover {
  opacity: 1;
}

/* ==========================================================================
   HTML Viewer
   ========================================================================== */

.html-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-base);
}

/* --- Viewer Header --- */
.viewer-header {
  background: var(--surface-base);
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.viewer-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* --- View Controls (Preview / Code toggle) --- */
.view-controls {
  display: flex;
  gap: 0;
  background: var(--surface-raised);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  padding: 2px;
}

.view-controls button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.375rem 0.875rem;
  border-radius: calc(var(--radius-md) - 2px);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.view-controls button.active {
  background: var(--accent-primary);
  color: var(--text-inverse);
  box-shadow: var(--shadow-sm);
}

.view-controls button:hover:not(.active) {
  background: var(--surface-highlight);
  color: var(--text-primary);
}

/* --- Header Buttons (History, Save Template, Full Screen) --- */
.history-btn,
.save-template-btn {
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

.history-btn:hover:not(:disabled),
.save-template-btn:hover:not(:disabled) {
  background: var(--surface-highlight);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.history-btn.active {
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.history-btn:disabled,
.save-template-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.fullscreen-btn,
.export-btn {
  background: var(--surface-highlight);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.fullscreen-btn:hover:not(:disabled),
.export-btn:hover:not(:disabled) {
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.fullscreen-btn:disabled,
.export-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* --- Viewer Body --- */
.viewer-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.viewer-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* --- Empty Placeholder --- */
.placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: var(--text-tertiary);
  text-align: center;
  background:
    linear-gradient(var(--border-subtle) 1px, transparent 1px),
    linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: center center;
}

.placeholder h3 {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-regular);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color: var(--text-tertiary);
  margin-bottom: 0.5rem;
}

.placeholder p {
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  opacity: 0.6;
}

.html-preview {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}

/* ==========================================================================
   Save Template Modal
   ========================================================================== */

.save-template-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.save-template-modal {
  background: var(--surface-overlay);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
  box-shadow: var(--shadow-lg);
  animation: modal-enter var(--duration-normal) var(--ease-out-expo);
}

.save-template-modal h3 {
  margin: 0 0 20px;
  font-family: var(--font-display);
  font-size: var(--fs-lg);
  font-weight: var(--fw-heavy);
  color: var(--text-primary);
}

.form-field {
  margin-bottom: 16px;
}

.form-field label {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.form-field input,
.form-field textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--fs-base);
  color: var(--text-primary);
  background: var(--surface-raised);
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--border-accent);
  box-shadow: var(--shadow-glow-accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.modal-actions button {
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.modal-actions button:hover:not(:disabled) {
  background: var(--surface-highlight);
  color: var(--text-primary);
}

.modal-actions .save-btn {
  background: var(--gradient-send-btn);
  color: white;
  border-color: transparent;
}

.modal-actions .save-btn:hover:not(:disabled) {
  background: var(--gradient-send-hover);
}

.modal-actions button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ==========================================================================
   Responsive
   ========================================================================== */

@media (max-width: 768px) {
  .chat-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .session-info {
    align-items: flex-start;
  }

  .viewer-header {
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
  }

  .view-controls {
    justify-content: center;
  }

  .status-indicator {
    font-size: var(--fs-xs);
    padding: 0.25rem 0.5rem;
  }
}
```

### 1.2 Rewrite `frontend/src/components/Layout/SplitPane.css`

Replace 3-dot divider with single vertical energy line. Add `.transmitting` class for processing state with conduit animation.

**File:** `frontend/src/components/Layout/SplitPane.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Split Pane Layout
   ========================================================================== */

.split-pane {
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
}

.split-pane-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  cursor: ew-resize;
  background: transparent;
  pointer-events: auto;
}

.split-pane-left,
.split-pane-right {
  height: 100%;
  overflow: hidden;
  transition: none;
}

.split-pane-left.dragging,
.split-pane-right.dragging {
  pointer-events: none;
  user-select: none;
}

.split-pane-left.dragging *,
.split-pane-right.dragging * {
  pointer-events: none !important;
  user-select: none !important;
}

.split-pane-left.dragging iframe,
.split-pane-right.dragging iframe {
  pointer-events: none !important;
}

/* --- Divider --- */
.split-pane-divider {
  width: 6px;
  background: var(--surface-void);
  cursor: ew-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out-expo);
  position: relative;
  user-select: none;
  flex-shrink: 0;
  border-left: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-subtle);
}

/* Resting vertical line */
.divider-line {
  width: 1px;
  height: 40px;
  background: var(--border-strong);
  border-radius: 1px;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.split-pane-divider:hover {
  width: 8px;
  background: var(--surface-highlight);
}

.split-pane-divider:hover .divider-line {
  background: var(--accent-primary);
  box-shadow: 0 0 8px var(--accent-primary-glow);
  height: 60px;
}

.split-pane-divider.dragging {
  width: 8px;
  background: var(--accent-primary-muted);
  border-color: var(--accent-primary);
  z-index: 10000;
}

.split-pane-divider.dragging .divider-line {
  background: var(--accent-primary);
  box-shadow: 0 0 16px var(--accent-primary-glow);
  height: 80px;
}

/* --- Transmitting State (active AI processing) --- */
.split-pane-divider.transmitting {
  background: var(--signal-active-muted);
  border-color: rgba(0, 229, 204, 0.1);
}

.split-pane-divider.transmitting .divider-line {
  background: var(--signal-active);
  box-shadow: 0 0 12px var(--signal-active-glow);
  animation: conduit-pulse 1.5s ease-in-out infinite;
}

/* Sweep overlay for transmitting */
.split-pane-divider.transmitting::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    var(--signal-active-glow) 50%,
    transparent 100%
  );
  background-size: 100% 60%;
  background-repeat: no-repeat;
  animation: conduit-sweep 2s linear infinite;
  pointer-events: none;
}

/* Dragging cursor overrides */
.split-pane.dragging {
  cursor: ew-resize !important;
}

.split-pane.dragging * {
  cursor: ew-resize !important;
}

/* --- Mobile Responsive --- */
@media (max-width: 768px) {
  .split-pane {
    flex-direction: column;
  }

  .split-pane-left,
  .split-pane-right {
    width: 100% !important;
  }

  .split-pane-left {
    height: 50% !important;
  }

  .split-pane-right {
    height: 50% !important;
  }

  .split-pane-divider {
    width: 100%;
    height: 6px;
    cursor: ns-resize;
    flex-direction: row;
    border-left: none;
    border-right: none;
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
  }

  .divider-line {
    width: 40px;
    height: 1px;
  }

  .split-pane-divider:hover .divider-line {
    width: 60px;
    height: 1px;
  }
}
```

### 1.3 Update `frontend/src/components/Layout/SplitPane.tsx`

Add `isProcessing` prop. Replace 3-dot divider markup with single `divider-line` element. Add `transmitting` class when processing.

**Changes to `SplitPane.tsx`:**

Replace the entire interface and component. Here are the exact changes:

**Change 1:** Update the interface to add `isProcessing` prop:

Find:
```typescript
interface SplitPaneProps {
  leftContent: React.ReactNode;
  rightContent: React.ReactNode;
  defaultPosition?: number;
  minSize?: number;
  maxSize?: number;
}
```

Replace with:
```typescript
interface SplitPaneProps {
  leftContent: React.ReactNode;
  rightContent: React.ReactNode;
  defaultPosition?: number;
  minSize?: number;
  maxSize?: number;
  isProcessing?: boolean;
}
```

**Change 2:** Update the component destructuring:

Find:
```typescript
const SplitPane: React.FC<SplitPaneProps> = ({
  leftContent,
  rightContent,
  defaultPosition = 50,
  minSize = 20,
  maxSize = 80
}) => {
```

Replace with:
```typescript
const SplitPane: React.FC<SplitPaneProps> = ({
  leftContent,
  rightContent,
  defaultPosition = 50,
  minSize = 20,
  maxSize = 80,
  isProcessing = false
}) => {
```

**Change 3:** Update the divider markup (replace dots with line):

Find:
```typescript
      <div
        className={`split-pane-divider ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
      >
        <div className="divider-handle">
          <div className="divider-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
```

Replace with:
```typescript
      <div
        className={`split-pane-divider ${isDragging ? 'dragging' : ''}${isProcessing ? ' transmitting' : ''}`}
        onMouseDown={handleMouseDown}
      >
        <div className="divider-line" />
      </div>
```

### 1.4 Update `frontend/src/App.tsx`

Pass `isStreaming` to SplitPane as `isProcessing` prop.

**Change:** In the `ChatApp` component, update the `<SplitPane>` JSX:

Find:
```typescript
      <SplitPane
        leftContent={
          <ChatWindow
```

Replace with:
```typescript
      <SplitPane
        isProcessing={isStreaming}
        leftContent={
          <ChatWindow
```

### Phase 1 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] App renders with dark theme, no hardcoded colors visible
- [ ] SplitPane divider shows single vertical line (not 3 dots)
- [ ] Divider glows blue on hover
- [ ] Divider shows cyan energy sweep when AI is processing
- [ ] View toggle (Preview/Code) has pill-shaped appearance
- [ ] All viewer header buttons (History, Save Template, Full Screen, Export) are styled
- [ ] Empty placeholder shows grid-paper background
- [ ] Save template modal is themed
- [ ] Error banner uses signal-error color

---

## Phase 2: Chat Pane (ChatWindow, MessageList, ChatInput)

### Objective
Restyle the chat pane: header with theme toggle, monospace status, redesigned messages with entrance animations, and themed input area.

### 2.1 Rewrite `frontend/src/components/ChatWindow/ChatWindow.css`

**File:** `frontend/src/components/ChatWindow/ChatWindow.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Chat Window
   ========================================================================== */

.chat-window {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-base);
  border-right: 1px solid var(--border-subtle);
}

/* --- Chat Header --- */
.chat-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-default);
  background: var(--gradient-header);
  color: var(--text-primary);
  position: relative;
  z-index: 10;
}

/* Subtle accent line at bottom of header */
.chat-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    var(--signal-active) 50%,
    transparent 100%
  );
  opacity: 0.3;
}

.chat-header h2 {
  margin: 0 0 0.5rem 0;
  font-family: var(--font-display);
  font-weight: var(--fw-thin);
  font-size: var(--fs-lg);
  letter-spacing: var(--tracking-tight);
  color: var(--text-primary);
}

.session-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.session-id {
  font-family: var(--font-mono);
  background: var(--surface-highlight);
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--fs-xs);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

/* --- Status Indicator (Monospace Diagnostic) --- */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-weight: var(--fw-regular);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  font-size: var(--fs-xs);
  border: 1px solid var(--border-subtle);
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.status-indicator.ready {
  background: var(--signal-active-muted);
  color: var(--signal-active);
  border-color: rgba(0, 229, 204, 0.15);
}

.status-indicator.processing {
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
  border-color: rgba(79, 106, 255, 0.2);
  animation: fade-pulse 2s ease-in-out infinite;
}

/* --- Responsive --- */
@media (max-width: 768px) {
  .chat-header {
    padding: 1rem 1.25rem;
  }

  .chat-header h2 {
    font-size: var(--fs-md);
    margin-bottom: 0.375rem;
  }

  .session-info {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .session-id,
  .status-indicator {
    font-size: var(--fs-xs);
    padding: 0.25rem 0.5rem;
  }
}

@media (max-width: 480px) {
  .chat-header {
    padding: 0.75rem 1rem;
  }

  .chat-header h2 {
    font-size: var(--fs-base);
  }

  .session-info {
    gap: 0.375rem;
  }
}
```

### 2.2 Rewrite `frontend/src/components/ChatWindow/MessageList.css`

**File:** `frontend/src/components/ChatWindow/MessageList.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Message List
   ========================================================================== */

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--surface-base);
}

/* --- Base Message --- */
.message {
  max-width: 85%;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: 0.25rem;
}

/* --- User Message --- */
.message-user {
  align-self: flex-end;
  background: var(--gradient-user-msg);
  color: var(--text-primary);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg);
  animation: fade-up var(--duration-normal) var(--ease-out-expo);
}

.message-user .message-header {
  color: var(--text-secondary);
}

.message-user .message-sender,
.message-user .message-timestamp {
  color: var(--text-secondary);
  font-weight: var(--fw-medium);
}

/* --- AI Message --- */
.message-ai {
  align-self: flex-start;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-left: 2px solid var(--accent-primary);
  border-radius: var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg);
  position: relative;
  animation: fade-left var(--duration-normal) var(--ease-out-expo);
}

.message-ai .message-header {
  color: var(--text-secondary);
}

.message-ai .message-sender,
.message-ai .message-timestamp {
  color: var(--text-secondary);
  font-weight: var(--fw-medium);
}

/* --- Message Header --- */
.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: var(--fs-sm);
}

.message-sender {
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  font-size: var(--fs-xs);
}

.message-timestamp {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

/* --- Message Content --- */
.message-content {
  line-height: var(--leading-relaxed);
  word-wrap: break-word;
  font-family: var(--font-body);
  font-size: var(--fs-base);
  white-space: pre-wrap;
  color: var(--text-primary);
}

.message-user .message-content {
  color: var(--text-primary);
  font-weight: var(--fw-regular);
}

.message-ai .message-content {
  color: var(--text-primary);
  font-weight: var(--fw-regular);
}

/* --- Processing / Streaming Message --- */
.message.processing {
  opacity: 0.9;
}

.message.processing .message-ai {
  border-left-color: var(--signal-active);
}

/* --- Streaming Indicator --- */
.streaming-label {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--signal-active);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.streaming-label .streaming-underscore {
  animation: cursor-blink 1s step-end infinite;
}

/* --- Typing Indicator (fallback before content streams) --- */
.typing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-right: 0.5rem;
}

.typing-indicator span {
  width: 5px;
  height: 5px;
  border-radius: var(--radius-full);
  background: var(--accent-primary);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* --- Responsive --- */
@media (max-width: 768px) {
  .message {
    max-width: 95%;
    padding: 0.875rem 1rem;
  }

  .message-list {
    padding: 0.75rem;
    gap: 0.75rem;
  }
}
```

### 2.3 Rewrite `frontend/src/components/ChatWindow/ChatInput.css`

**File:** `frontend/src/components/ChatWindow/ChatInput.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Chat Input
   ========================================================================== */

.chat-input-container {
  display: flex;
  flex-direction: column;
  padding: 1.25rem 1.5rem;
  background: var(--surface-base);
  border-top: 1px solid var(--border-default);
}

/* --- Content Hint --- */
.content-hint {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  background: var(--accent-primary-muted);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-lg);
  font-size: var(--fs-base);
  color: var(--accent-primary);
  animation: fade-up var(--duration-normal) var(--ease-out-expo);
}

.hint-icon {
  font-size: var(--fs-md);
  flex-shrink: 0;
}

/* --- Input Wrapper --- */
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  background: var(--surface-raised);
  padding: 0.875rem 1rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.input-wrapper:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

.input-wrapper:focus-within {
  border-color: var(--border-accent);
  box-shadow: var(--shadow-glow-accent);
}

/* --- Textarea --- */
.chat-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-body);
  font-size: var(--fs-base);
  line-height: var(--leading-normal);
  color: var(--text-primary);
  background: transparent;
  min-height: 24px;
  max-height: 300px;
  overflow-y: hidden;
  transition: color var(--duration-fast);
}

.chat-textarea::placeholder {
  color: var(--text-tertiary);
  font-weight: var(--fw-light);
}

.chat-textarea:disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
  opacity: 0.6;
}

/* --- Send Button --- */
.send-button {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-send-btn);
  color: white;
  box-shadow: var(--shadow-glow-accent);
  flex-shrink: 0;
}

.send-button:hover:not(:disabled) {
  background: var(--gradient-send-hover);
  transform: translateY(-1px);
  box-shadow: 0 0 24px var(--accent-primary-glow);
}

.send-button:active:not(:disabled) {
  transform: translateY(0) scale(0.95);
  animation: summon-pulse var(--duration-dramatic) var(--ease-out-expo);
}

.send-button:disabled {
  background: var(--surface-highlight);
  color: var(--text-tertiary);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* --- Loading Dots (inside send button during processing) --- */
.loading-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.loading-dots span {
  width: 5px;
  height: 5px;
  border-radius: var(--radius-full);
  background: var(--accent-primary);
  animation: glowingDots 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0s;
}

@keyframes glowingDots {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* --- Input Footer --- */
.input-footer {
  margin-top: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  padding: 0 0.25rem;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* --- Footer Action Buttons --- */
.add-visual-btn,
.attach-file-btn {
  background: none;
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.add-visual-btn:hover:not(:disabled),
.attach-file-btn:hover:not(:disabled) {
  border-color: var(--border-accent);
  color: var(--accent-primary);
  background: var(--accent-primary-muted);
}

.add-visual-btn:disabled,
.attach-file-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.char-count {
  font-family: var(--font-mono);
  font-weight: var(--fw-medium);
  font-size: var(--fs-xs);
}

.help-text {
  font-weight: var(--fw-light);
  opacity: 0.7;
  font-size: var(--fs-xs);
}

/* ==========================================================================
   File Upload Indicators
   ========================================================================== */

.attached-file-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--accent-primary-muted);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  color: var(--accent-primary);
  animation: fade-up var(--duration-normal) var(--ease-out-expo);
}

.attached-file-indicator .file-icon {
  flex-shrink: 0;
  opacity: 0.7;
}

.attached-file-name {
  flex: 1;
  font-family: var(--font-mono);
  font-weight: var(--fw-medium);
  font-size: var(--fs-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-attachment {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--duration-fast);
}

.remove-attachment:hover {
  color: var(--signal-error);
  background: var(--signal-error-muted);
}

/* --- Upload Error --- */
.upload-error-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--signal-error-muted);
  border: 1px solid var(--signal-error);
  border-radius: var(--radius-md);
  font-size: var(--fs-sm);
  color: var(--signal-error);
  animation: fade-up var(--duration-normal) var(--ease-out-expo);
}

.upload-error-banner span {
  flex: 1;
}

.upload-error-banner button {
  background: none;
  border: none;
  color: var(--signal-error);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: background var(--duration-fast);
}

.upload-error-banner button:hover {
  background: var(--signal-error-muted);
}

/* ==========================================================================
   Responsive
   ========================================================================== */

@media (max-width: 768px) {
  .chat-input-container {
    padding: 1rem;
  }

  .input-wrapper {
    gap: 0.5rem;
    padding: 0.75rem;
    border-radius: var(--radius-lg);
  }

  .chat-textarea {
    font-size: 16px; /* Prevents zoom on iOS */
    max-height: 200px;
  }

  .send-button {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-md);
  }

  .input-footer {
    font-size: var(--fs-xs);
    margin-top: 0.5rem;
  }

  .footer-right {
    gap: 0.75rem;
  }
}

@media (max-width: 480px) {
  .chat-input-container {
    padding: 0.75rem;
  }

  .input-wrapper {
    gap: 0.375rem;
    padding: 0.625rem;
    border-radius: var(--radius-md);
  }

  .send-button {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
  }

  .input-footer {
    font-size: var(--fs-xs);
    gap: 0.5rem;
    flex-direction: column;
    align-items: flex-start;
  }

  .footer-left,
  .footer-right {
    width: 100%;
    justify-content: space-between;
  }

  .footer-right {
    gap: 0.5rem;
    margin-top: 0.375rem;
  }
}
```

### 2.4 Update `frontend/src/components/ChatWindow/MessageList.tsx`

Change "AI Assistant" label to "ARCHITECT" in two places (line 57 and line 76).

**Change 1:** In the message list rendering (line 57 area):

Find:
```typescript
              {message.role === 'user' ? 'You' : 'AI Assistant'}
```

Replace with:
```typescript
              {message.role === 'user' ? 'You' : 'ARCHITECT'}
```

**Change 2:** In the streaming message block (line 76 area):

Find:
```typescript
            <span className="message-sender">AI Assistant</span>
```

Replace with:
```typescript
            <span className="message-sender">ARCHITECT</span>
```

### 2.5 Update `frontend/src/components/ChatWindow/index.tsx`

Add ThemeToggle to the chat header. Update the status indicator text to use diagnostic format.

**Change 1:** Add ThemeToggle import at the top:

Find:
```typescript
import './ChatWindow.css';
```

Replace with:
```typescript
import ThemeToggle from '../ThemeToggle';
import './ChatWindow.css';
```

**Change 2:** Update the header JSX to include ThemeToggle and diagnostic status text:

Find:
```typescript
      <div className="chat-header">
        <h2>AI HTML Builder</h2>
        <div className="session-info">
          <div className={`status-indicator ${isStreaming ? 'processing' : 'ready'}`}>
            {isStreaming ? (currentStatus || 'Processing...') : 'Ready'}
          </div>
        </div>
      </div>
```

Replace with:
```typescript
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2>AI HTML Builder</h2>
          <ThemeToggle />
        </div>
        <div className="session-info">
          <div className={`status-indicator ${isStreaming ? 'processing' : 'ready'}`}>
            {isStreaming ? `[>] ${currentStatus || 'PROCESSING...'}` : '[*] SYSTEMS NOMINAL'}
          </div>
        </div>
      </div>
```

### Phase 2 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] Chat header shows "AI HTML Builder" with ThemeToggle button on right
- [ ] Status shows `[*] SYSTEMS NOMINAL` when idle (cyan/teal)
- [ ] Status shows `[>] PROCESSING...` when streaming (blue, pulsing)
- [ ] User messages appear from right with fade-up animation
- [ ] AI messages appear from left with fade-left animation and 2px accent left border
- [ ] AI messages show "ARCHITECT" label (not "AI Assistant")
- [ ] Send button has gradient background, glows on hover
- [ ] Input wrapper has subtle glow on focus
- [ ] Theme toggle switches between dark and light modes
- [ ] Footer buttons (attach file, add visual) are monospace uppercase

---

## Phase 3: Viewer Pane (DocumentTabs, CodeView, VersionTimeline, Export)

### Objective
Restyle all viewer-side components with CSS variables. Remove all dark mode media queries.

### 3.1 Rewrite `frontend/src/components/DocumentTabs/DocumentTabs.css`

**File:** `frontend/src/components/DocumentTabs/DocumentTabs.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Document Tabs
   ========================================================================== */

.document-tabs-container {
  display: flex;
  align-items: center;
  background: var(--surface-void);
  border-bottom: 1px solid var(--border-default);
  padding: 0 4px;
  overflow-x: auto;
  overflow-y: hidden;
  flex-shrink: 0;
}

.document-tabs {
  display: flex;
  gap: 1px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.document-tabs::-webkit-scrollbar {
  height: 3px;
}

.document-tabs::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 2px;
}

.document-tab {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  background: var(--surface-raised);
  color: var(--text-secondary);
  border: none;
  border-top: 2px solid transparent;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
  min-width: 80px;
  max-width: 200px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  letter-spacing: var(--tracking-normal);
}

.document-tab:hover {
  background: var(--surface-highlight);
  color: var(--text-primary);
}

.document-tab.active {
  background: var(--surface-base);
  border-top-color: var(--accent-primary);
  color: var(--text-primary);
  font-weight: var(--fw-medium);
}

.tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
}
```

### 3.2 Rewrite `frontend/src/components/CodeViewer/CodeView.css`

**File:** `frontend/src/components/CodeViewer/CodeView.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Code View (CodeMirror wrapper)
   ========================================================================== */

.code-view-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-void);
  overflow: hidden;
}

.code-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.code-view-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.code-view-body {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.codemirror-container {
  height: 100%;
}

.codemirror-container .cm-editor {
  height: 100%;
}

.copy-button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  cursor: pointer;
  transition: background var(--duration-fast);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.copy-button:hover {
  background: var(--accent-primary-hover);
}
```

### 3.3 Rewrite `frontend/src/components/VersionHistory/VersionTimeline.css`

**File:** `frontend/src/components/VersionHistory/VersionTimeline.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Version Timeline
   ========================================================================== */

.version-timeline {
  display: flex;
  flex-direction: column;
  width: 260px;
  min-width: 260px;
  border-left: 1px solid var(--border-default);
  background: var(--surface-base);
  height: 100%;
  overflow: hidden;
}

.version-timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-raised);
  flex-shrink: 0;
}

.version-timeline-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.version-timeline-close {
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  transition: color var(--duration-fast);
}

.version-timeline-close:hover {
  color: var(--text-primary);
}

.version-timeline-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-timeline-empty,
.version-timeline-error {
  padding: 24px 12px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.version-timeline-error {
  color: var(--signal-error);
}

/* --- Version Preview Bar --- */
.version-preview-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: var(--signal-warning-muted);
  border-bottom: 1px solid var(--signal-warning);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--signal-warning);
  flex-shrink: 0;
}

.back-to-current-btn {
  background: none;
  border: 1px solid var(--signal-warning);
  color: var(--signal-warning);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.back-to-current-btn:hover {
  background: var(--signal-warning);
  color: var(--text-inverse);
}

/* --- Version Item --- */
.version-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px;
  margin-bottom: 6px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  cursor: pointer;
  transition: border-color var(--duration-fast), background var(--duration-fast);
  font-family: inherit;
  font-size: inherit;
}

.version-item:hover {
  border-color: var(--border-strong);
  background: var(--surface-highlight);
}

.version-item--selected {
  border-color: var(--accent-primary);
  background: var(--accent-primary-muted);
}

.version-item--current {
  border-left: 3px solid var(--signal-success);
}

.version-item-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.version-number {
  font-family: var(--font-mono);
  font-weight: var(--fw-bold);
  font-size: var(--fs-xs);
  color: var(--text-primary);
}

.version-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  font-weight: var(--fw-medium);
}

.version-badge--current {
  background: var(--signal-success-muted);
  color: var(--signal-success);
}

.version-model {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
}

.version-summary {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.version-prompt {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.version-time {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
}
```

### 3.4 Rewrite `frontend/src/components/Export/ExportDropdown.css`

**File:** `frontend/src/components/Export/ExportDropdown.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Export Dropdown
   ========================================================================== */

.export-dropdown {
  position: relative;
}

.export-dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 180px;
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 50;
  overflow: hidden;
  animation: dropdown-enter var(--duration-fast) var(--ease-out-expo);
}

.export-dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 14px;
  background: none;
  border: none;
  text-align: left;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  cursor: pointer;
  transition: background var(--duration-fast);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.export-dropdown-item:hover:not(:disabled) {
  background: var(--surface-highlight);
  color: var(--accent-primary);
}

.export-dropdown-item:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.export-dropdown-item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.coming-soon {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-style: italic;
  text-transform: none;
  letter-spacing: var(--tracking-normal);
}

.export-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--signal-error-muted);
  border-bottom: 1px solid var(--signal-error);
  color: var(--signal-error);
  font-size: var(--fs-sm);
}

.export-error button {
  background: none;
  border: none;
  color: var(--signal-error);
  cursor: pointer;
  font-size: var(--fs-md);
  padding: 0 4px;
}

.export-loading {
  color: var(--text-tertiary);
  font-style: italic;
}
```

### Phase 3 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] Document tabs use dark theme, active tab has accent top border
- [ ] Code view has dark background, copy button is accent-colored
- [ ] Version timeline items have proper borders, model badges use accent colors
- [ ] Version preview bar uses warning-yellow colors
- [ ] Export dropdown appears with dropdown-enter animation
- [ ] All components respond to theme toggle (dark/light)

---

## Phase 4: Modals & Cards (PromptLibraryModal, TemplateCards, PromptLibraryButton)

### Objective
Restyle the prompt library modal, template cards in empty state, and the prompt library button.

### 4.1 Rewrite `frontend/src/components/ChatWindow/PromptLibraryModal.css`

**File:** `frontend/src/components/ChatWindow/PromptLibraryModal.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Prompt Library Modal
   ========================================================================== */

.prompt-library-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--duration-fast) var(--ease-out-expo);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.prompt-library-modal {
  width: 90%;
  max-width: 1000px;
  height: 80vh;
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: modal-enter var(--duration-normal) var(--ease-out-expo);
}

/* --- Modal Header --- */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-base);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.modal-header h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--fs-xl);
  font-weight: var(--fw-heavy);
  color: var(--text-primary);
}

.close-button {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border-default);
  background: var(--surface-highlight);
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.close-button:hover {
  background: var(--signal-error-muted);
  border-color: var(--signal-error);
  color: var(--signal-error);
}

/* --- Modal Content Layout --- */
.modal-content {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* --- Sidebar --- */
.templates-sidebar {
  width: 350px;
  background: var(--surface-base);
  border-right: 1px solid var(--border-default);
  padding: 1.5rem;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-description {
  margin: 0 0 1.5rem 0;
  color: var(--text-tertiary);
  font-size: var(--fs-base);
  line-height: var(--leading-normal);
}

/* --- Category Group --- */
.category-group {
  margin-bottom: 2rem;
}

.category-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  margin: 0 0 0.75rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-default);
}

/* --- Template Item --- */
.template-item {
  width: 100%;
  text-align: left;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 1rem;
  margin-bottom: 0.75rem;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}

.template-item:hover {
  border-color: var(--border-accent);
  box-shadow: var(--shadow-glow-accent);
  transform: translateY(-1px);
}

.template-item.active {
  border-color: var(--accent-primary);
  background: var(--accent-primary-muted);
  box-shadow: var(--shadow-glow-accent);
}

.template-name {
  font-family: var(--font-body);
  font-weight: var(--fw-medium);
  color: var(--text-primary);
  margin-bottom: 0.25rem;
  font-size: var(--fs-base);
}

.template-description {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}

/* --- Preview Area --- */
.template-preview {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  background: var(--surface-overlay);
}

.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-tertiary);
}

.placeholder-content svg {
  margin-bottom: 1rem;
  opacity: 0.3;
}

.placeholder-content h3 {
  margin: 0 0 0.5rem 0;
  font-family: var(--font-display);
  color: var(--text-secondary);
}

.placeholder-content p {
  margin: 0;
  font-size: var(--fs-base);
}

/* --- Preview Content --- */
.preview-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-default);
}

.preview-header h3 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: var(--fw-heavy);
  color: var(--text-primary);
  font-size: var(--fs-lg);
}

.template-category {
  background: var(--accent-primary-muted);
  color: var(--accent-primary);
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.template-full-description {
  color: var(--text-secondary);
  margin: 0 0 1.5rem 0;
  line-height: var(--leading-normal);
}

/* --- Template Preview Text --- */
.template-preview-text {
  flex: 1;
  margin-bottom: 1.5rem;
}

.template-preview-text h4 {
  margin: 0 0 1rem 0;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.template-text {
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  line-height: var(--leading-normal);
  color: var(--text-primary);
  max-height: 300px;
  overflow-y: auto;
}

.section-header {
  font-weight: var(--fw-bold);
  color: var(--accent-primary);
  margin: 1rem 0 0.5rem 0;
}

.section-header:first-child {
  margin-top: 0;
}

.template-line {
  color: var(--text-secondary);
  margin: 0.25rem 0;
}

.template-line:empty {
  margin: 0.5rem 0;
}

/* --- Use Template Button --- */
.preview-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid var(--border-default);
}

.use-template-button {
  background: var(--gradient-send-btn);
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-weight: var(--fw-bold);
  font-size: var(--fs-sm);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  box-shadow: var(--shadow-glow-accent);
}

.use-template-button:hover {
  background: var(--gradient-send-hover);
  transform: translateY(-1px);
  box-shadow: 0 0 24px var(--accent-primary-glow);
}

/* ==========================================================================
   Responsive
   ========================================================================== */

@media (max-width: 768px) {
  .prompt-library-modal {
    width: 95%;
    height: 85vh;
  }

  .modal-header {
    padding: 1rem 1.5rem;
  }

  .modal-header h2 {
    font-size: var(--fs-lg);
  }

  .modal-content {
    flex-direction: column;
  }

  .templates-sidebar {
    width: 100%;
    height: 40%;
    border-right: none;
    border-bottom: 1px solid var(--border-default);
    padding: 1rem;
  }

  .template-preview {
    padding: 1rem;
    height: 60%;
  }

  .close-button {
    width: 36px;
    height: 36px;
  }
}

@media (max-width: 480px) {
  .prompt-library-modal {
    width: 98%;
    height: 90vh;
    border-radius: var(--radius-lg);
  }

  .modal-header {
    padding: 0.75rem 1rem;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  .modal-header h2 {
    font-size: var(--fs-md);
  }

  .templates-sidebar {
    padding: 0.75rem;
  }

  .template-preview {
    padding: 0.75rem;
  }

  .template-item {
    padding: 0.75rem;
  }

  .use-template-button {
    padding: 0.6rem 1.5rem;
    font-size: var(--fs-xs);
  }
}
```

### 4.2 Rewrite `frontend/src/components/EmptyState/TemplateCards.css`

**File:** `frontend/src/components/EmptyState/TemplateCards.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Template Cards (Empty State)
   ========================================================================== */

.template-cards {
  padding: 24px 16px 16px;
}

.template-cards-heading {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-regular);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
  color: var(--text-tertiary);
  text-align: center;
  margin: 0 0 16px;
}

.template-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

/* --- Template Card --- */
.template-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: all var(--duration-fast) var(--ease-out-expo);
  font-family: inherit;
  position: relative;
  overflow: hidden;
  animation: card-enter var(--duration-normal) var(--ease-out-expo) backwards;
}

/* Staggered entrance */
.template-card:nth-child(1)  { animation-delay: 0ms; }
.template-card:nth-child(2)  { animation-delay: 50ms; }
.template-card:nth-child(3)  { animation-delay: 100ms; }
.template-card:nth-child(4)  { animation-delay: 150ms; }
.template-card:nth-child(5)  { animation-delay: 200ms; }
.template-card:nth-child(6)  { animation-delay: 250ms; }
.template-card:nth-child(7)  { animation-delay: 300ms; }
.template-card:nth-child(8)  { animation-delay: 350ms; }

/* Accent border slide-in on hover via ::before */
.template-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 2px;
  height: 0;
  background: var(--accent-primary);
  transition: height var(--duration-normal) var(--ease-out-expo);
}

.template-card:hover {
  border-color: var(--border-accent);
  box-shadow: var(--shadow-glow-accent);
  transform: translateY(-2px);
}

.template-card:hover::before {
  height: 100%;
}

.template-card-icon {
  font-size: 20px;
  line-height: 1;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary-muted);
  border-radius: var(--radius-md);
}

.template-card-title {
  font-family: var(--font-body);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
  color: var(--text-primary);
}

.template-card-desc {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  line-height: var(--leading-normal);
}

/* ==========================================================================
   Custom Template Cards
   ========================================================================== */

.custom-templates-grid {
  margin-bottom: 20px;
}

.custom-template-card {
  position: relative;
}

.custom-template-thumb {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
}

.delete-template-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--duration-fast);
}

.custom-template-card:hover .delete-template-btn {
  opacity: 1;
}

.delete-template-btn:hover {
  background: var(--signal-error);
}

/* --- Responsive --- */
@media (max-width: 480px) {
  .template-cards-grid {
    grid-template-columns: 1fr;
  }
}
```

### 4.3 Rewrite `frontend/src/components/ChatWindow/PromptLibraryButton.css`

**File:** `frontend/src/components/ChatWindow/PromptLibraryButton.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Prompt Library Button
   ========================================================================== */

.prompt-library-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--surface-highlight);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
  white-space: nowrap;
  height: auto;
}

.prompt-library-button:hover:not(:disabled) {
  background: var(--accent-primary-muted);
  border-color: var(--border-accent);
  color: var(--accent-primary);
}

.prompt-library-button:active:not(:disabled) {
  transform: scale(0.97);
}

.prompt-library-button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.template-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* --- Mobile --- */
@media (max-width: 768px) {
  .prompt-library-button {
    padding: 0.3rem 0.5rem;
    font-size: var(--fs-xs);
  }

  .template-icon {
    width: 12px;
    height: 12px;
  }
}

@media (max-width: 480px) {
  .prompt-library-button {
    padding: 0.25rem 0.4rem;
  }

  .template-icon {
    width: 11px;
    height: 11px;
  }
}
```

### Phase 4 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] Prompt library button styled with monospace uppercase
- [ ] Prompt library modal opens with modal-enter animation
- [ ] Modal header has NO blue gradient (uses surface-base + border)
- [ ] Sidebar templates have accent border on active state
- [ ] "Use Template" button has gradient style matching send button
- [ ] Template cards in empty state have staggered entrance animation
- [ ] Template card hover shows left accent border sliding in
- [ ] Emoji icons render on accent-primary-muted background
- [ ] All elements respond to theme toggle

---

## Phase 5: Streaming Polish (StreamingMarkdown)

### Objective
Restyle the streaming markdown renderer and code blocks with CSS variables.

### 5.1 Rewrite `frontend/src/components/Chat/StreamingMarkdown.css`

**File:** `frontend/src/components/Chat/StreamingMarkdown.css` (COMPLETE REPLACEMENT)

```css
/* ==========================================================================
   Streaming Markdown
   ========================================================================== */

.markdown-content {
  font-family: var(--font-body);
  font-size: var(--fs-base);
  line-height: var(--leading-relaxed);
  color: var(--text-primary);
}

.markdown-content p {
  margin: 0 0 8px 0;
}

.markdown-content p:last-child {
  margin-bottom: 0;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
  margin: 12px 0 6px 0;
  font-family: var(--font-display);
  color: var(--text-primary);
}

.markdown-content h1 { font-size: 18px; font-weight: var(--fw-heavy); }
.markdown-content h2 { font-size: 16px; font-weight: var(--fw-bold); }
.markdown-content h3 { font-size: 15px; font-weight: var(--fw-bold); }

.markdown-content ul,
.markdown-content ol {
  margin: 6px 0;
  padding-left: 20px;
}

.markdown-content li {
  margin: 3px 0;
}

/* --- Inline Code --- */
.markdown-content code {
  background: var(--surface-highlight);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--accent-primary);
}

/* --- Code Blocks --- */
.markdown-content pre {
  margin: 0;
  padding: 10px;
  overflow-x: auto;
  background: var(--surface-void);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.markdown-content pre code {
  background: none;
  padding: 0;
  font-size: 13px;
  color: var(--text-primary);
}

.code-block-wrapper {
  margin: 8px 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-void);
  border: 1px solid var(--border-default);
}

.code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 10px;
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-default);
}

.code-block-lang {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  font-weight: var(--fw-medium);
  letter-spacing: var(--tracking-wide);
}

.code-block-header .copy-button {
  padding: 2px 6px;
  font-size: 11px;
}

/* --- Tables --- */
.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.markdown-content th,
.markdown-content td {
  border: 1px solid var(--border-default);
  padding: 6px 10px;
  text-align: left;
  font-size: 13px;
}

.markdown-content th {
  background: var(--surface-raised);
  font-weight: var(--fw-medium);
  color: var(--text-secondary);
}

/* --- Blockquote --- */
.markdown-content blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--accent-primary);
  background: var(--accent-primary-muted);
  color: var(--text-secondary);
}

/* --- Streaming Cursor --- */
.streaming-cursor {
  display: inline-block;
  width: 8px;
  height: 1.1em;
  background: var(--signal-active);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: cursor-blink 1s step-end infinite;
}

/* --- highlight.js Dark Theme (default, works with dark-first approach) --- */
.hljs {
  background: transparent !important;
  color: var(--text-primary);
}

.hljs-keyword { color: #569cd6; }
.hljs-string { color: #ce9178; }
.hljs-comment { color: #6a9955; }
.hljs-tag { color: #4ec9b0; }
.hljs-attr { color: #9cdcfe; }
.hljs-number { color: #b5cea8; }
.hljs-built_in { color: #dcdcaa; }

/* --- highlight.js Light Theme Override --- */
[data-theme="light"] .hljs { color: #24292e; }
[data-theme="light"] .hljs-keyword { color: #d73a49; }
[data-theme="light"] .hljs-string { color: #032f62; }
[data-theme="light"] .hljs-comment { color: #6a737d; }
[data-theme="light"] .hljs-tag { color: #22863a; }
[data-theme="light"] .hljs-attr { color: #6f42c1; }
[data-theme="light"] .hljs-number { color: #005cc5; }
[data-theme="light"] .hljs-built_in { color: #e36209; }
```

### Phase 5 Verification

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Manual checks:
- [ ] Streaming cursor is a solid cyan block (not a pipe character)
- [ ] Inline code has accent-colored text on surface-highlight background
- [ ] Code blocks have dark background with proper syntax highlighting
- [ ] Switching to light theme changes syntax highlighting colors
- [ ] Tables and blockquotes use themed borders and backgrounds

---

## Phase 6: Integration & Wiring Verification

### Objective
Verify all components are properly wired and the full user flow works end-to-end.

### 6.1 Verify `isProcessing` prop chain

The `isStreaming` state flows through this chain:

```
useSSEChat (isStreaming)
  -> ChatApp component (const { isStreaming } = useSSEChat)
    -> SplitPane (isProcessing={isStreaming})  [Changed in Phase 1.4]
      -> .split-pane-divider.transmitting      [CSS in Phase 1.2]
```

This was already wired in Phase 1. Verify it works:
1. Send a message that triggers AI generation
2. The divider should show cyan energy sweep animation during processing
3. The divider returns to resting state when streaming completes

### 6.2 Verify theme toggle persistence

1. Click the sun/moon toggle in the chat header
2. Theme should switch immediately (no page reload)
3. Refresh the page - theme should persist
4. Open a new browser tab - theme should be correct from first paint (no flash)

### 6.3 Full verification commands

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

---

## Final Verification Checklist

### Build Quality
- [ ] `npx tsc --noEmit` - zero TypeScript errors
- [ ] `npm run build` - zero Vite build errors
- [ ] `npm run lint` - zero ESLint errors
- [ ] No console errors or warnings in browser DevTools

### Visual Verification - Dark Mode (Default)
- [ ] App background is near-black (#0D0F12)
- [ ] Chat header uses gradient-header, no blue gradient
- [ ] Status indicator shows monospace diagnostic format `[*] SYSTEMS NOMINAL`
- [ ] ThemeToggle button visible in chat header (sun icon)
- [ ] User messages have purple gradient background, rounded corners
- [ ] AI messages have raised surface background, 2px accent left border
- [ ] AI messages labeled "ARCHITECT" (not "AI Assistant")
- [ ] Send button has purple-blue gradient
- [ ] SplitPane divider shows single vertical line (not 3 dots)
- [ ] Divider glows blue on hover
- [ ] Empty viewer shows grid-paper background with "No content yet"
- [ ] All buttons use monospace uppercase font
- [ ] Template cards in empty state have staggered entrance animation
- [ ] Prompt library modal has dark theme (no blue header gradient)
- [ ] Scrollbars are thin and themed
- [ ] Code blocks have dark background in chat messages

### Visual Verification - Light Mode
- [ ] Click ThemeToggle - switches to light theme
- [ ] Background becomes warm off-white (#F7F5F2)
- [ ] All text is readable with sufficient contrast
- [ ] Accent colors shift to deeper blue/purple
- [ ] Code syntax highlighting uses light theme colors
- [ ] All components properly themed (no dark remnants)

### Functional Verification
- [ ] Chat message sending works
- [ ] Template selection works (both empty state cards and prompt library)
- [ ] File upload indicator appears and can be dismissed
- [ ] Export dropdown opens and closes
- [ ] Version history panel opens and closes
- [ ] Document tab switching works
- [ ] Code view and preview toggle work
- [ ] Save template modal opens, validates input, saves
- [ ] Full screen button opens new tab
- [ ] Error banner appears and can be dismissed
- [ ] SplitPane divider dragging still works smoothly
- [ ] Theme persists across page refresh

### Zero Regressions
- [ ] No `@media (prefers-color-scheme: dark)` anywhere in codebase
- [ ] No hardcoded color values in component CSS files
- [ ] No system fonts (Segoe UI, Roboto, Arial) in component CSS files
- [ ] No backend files modified
- [ ] No new npm dependencies added

---

## Note on Plan 009b

After this plan (009a) is complete, the existing Plan 009 should be updated:

1. **Rename file**: `009_VIEWER_PANE_UX_POLISH.md` -> `009b_VIEWER_PANE_UX_POLISH.md`
2. **Add dependency**: "Plan 009a (Visual Foundation) must be COMPLETE before starting 009b"
3. **Update dark mode rule**: Change `All new UI elements support dark mode (@media (prefers-color-scheme: dark))` to `All new UI elements use CSS variables from theme.css - NO media query dark mode`
4. **CSS requirement**: All new CSS in Plan 009b must use CSS custom properties from `theme.css` exclusively. Zero hardcoded colors, fonts, or shadows.
5. **Theme compatibility**: All new components must work in both dark and light themes without additional `[data-theme="light"]` overrides where possible (use semantic variables).

---

## Files Changed Summary

### New Files (2)
| File | Purpose |
|------|---------|
| `frontend/src/theme.css` | All CSS custom properties + keyframe animations |
| `frontend/src/components/ThemeToggle.tsx` | Sun/moon theme toggle component |

### Replaced CSS Files (14)
| File | Lines Before | Key Changes |
|------|-------------|-------------|
| `frontend/src/index.css` | 33 | Variables, scrollbar theming, theme-toggle style |
| `frontend/src/App.css` | 541 | All dark blocks removed, variables throughout |
| `frontend/src/components/Layout/SplitPane.css` | 155 | Energy line divider, transmitting animation |
| `frontend/src/components/ChatWindow/ChatWindow.css` | 156 | Monospace status, gradient header, accent line |
| `frontend/src/components/ChatWindow/ChatInput.css` | 507 | Themed input, gradient send button, summon-pulse |
| `frontend/src/components/ChatWindow/MessageList.css` | 203 | Entrance animations, asymmetric radius, accent border |
| `frontend/src/components/ChatWindow/PromptLibraryModal.css` | 472 | Dark modal, no blue header, modal-enter animation |
| `frontend/src/components/ChatWindow/PromptLibraryButton.css` | 68 | Monospace uppercase, accent hover |
| `frontend/src/components/Chat/StreamingMarkdown.css` | 201 | Cyan block cursor, themed code blocks, hljs overrides |
| `frontend/src/components/CodeViewer/CodeView.css` | 73 | Dark background, themed header |
| `frontend/src/components/DocumentTabs/DocumentTabs.css` | 89 | Dark tabs, accent top border |
| `frontend/src/components/VersionHistory/VersionTimeline.css` | 268 | All variables, themed badges |
| `frontend/src/components/EmptyState/TemplateCards.css` | 141 | Staggered card-enter, accent border slide-in |
| `frontend/src/components/Export/ExportDropdown.css` | 93 | dropdown-enter animation, themed items |

### Modified TSX Files (6)
| File | Changes |
|------|---------|
| `frontend/index.html` | Google Fonts, theme init script |
| `frontend/src/main.tsx` | Import theme.css before index.css |
| `frontend/src/App.tsx` | Pass `isProcessing={isStreaming}` to SplitPane |
| `frontend/src/components/Layout/SplitPane.tsx` | Add `isProcessing` prop, replace dots with line |
| `frontend/src/components/ChatWindow/index.tsx` | Add ThemeToggle, diagnostic status text |
| `frontend/src/components/ChatWindow/MessageList.tsx` | "AI Assistant" -> "ARCHITECT" |
