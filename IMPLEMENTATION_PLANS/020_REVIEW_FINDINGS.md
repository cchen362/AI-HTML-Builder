# Plan 020: Comprehensive Review Findings

**Date**: February 2026
**Status**: REVIEWED — Decisions made. PROCEED items in Plan 021.

Two independent reviews were conducted from a fresh perspective:
- **UX Review**: Is the app actually useful? Would people want to use it?
- **Architecture Review**: Is the codebase clean? Any bloat, redundancy, or hidden problems?

---

## UX Findings

### U1: No Session History (CRITICAL)

**What it means**: When a user starts a new session or closes the browser, their previous work disappears from the UI. The data is still saved in the database, but there's no way to get back to it. It's like writing a document in Word but having no "Recent Files" list.

**Implication**: Users who work on documents across multiple days lose access to their work. They'd have to complete everything in one sitting or lose it. For a corporate tool, this is a deal-breaker — people don't finish reports in one sitting.

**Decision**: `PROCEED` → Plan 021 Phase 1 (Auth) + Phase 2 (Session Browser)

---

### U2: No Regenerate / Edit on Messages (HIGH)

**What it means**: If the AI misunderstands your request, you have to retype the entire message from scratch. There's no "try again" button on AI responses and no "edit" button on your own messages. Every AI chat tool (ChatGPT, Claude, Copilot) has both of these.

**Implication**: Every AI mistake is expensive — users waste time retyping. After a few bad experiences, they'll start writing shorter, less detailed prompts (which actually makes the AI perform worse). Frustration compounds.

**Decision**: `DEFER` — Low ROI for short prompts typical in this tool

---

### U3: No Version Diff View (HIGH)

**What it means**: When the AI edits your document, you can see the version history (v1, v2, v3...) but you can't see *what actually changed* between versions. It's like having Git without `git diff`. Users have to manually eyeball the differences or just trust the AI.

**Implication**: The entire selling point of this tool is "surgical editing" — precise, targeted changes. But users can't verify that. If the AI says "Changed the header color," the user has no way to confirm it didn't also change something else. Trust erodes over time.

**Decision**: `PROCEED` → Plan 021 Phase 3 (Before/After toggle in version history)

---

### U4: No Undo / Ctrl+Z (MEDIUM)

**What it means**: If the AI makes a bad edit, reverting it requires: open version history panel → find the previous version → click restore → confirm the dialog. That's 4-5 clicks for what should be one keystroke (Ctrl+Z).

**Implication**: Users with muscle memory from Word/Google Docs will instinctively hit Ctrl+Z and nothing will happen. Mildly frustrating every time, especially during rapid iteration cycles.

**Decision**: `DEFER` — Version restore works; U3 diff view improves visibility

---

### U5: Theme Misaligned with Audience (MEDIUM)

**What it means**: The "Cyberpunk Amethyst" dark theme uses mint green text on dark purple backgrounds, gold accents, and ALL-CAPS MONOSPACE text everywhere. It looks like a hacker terminal or a sci-fi game. The intended users spend their days in Outlook, Teams, and SharePoint — neutral whites, grays, and blues.

**Implication**: The app feels "alien" to corporate users. It signals "developer toy" rather than "business productivity tool." It's not broken, but it creates a subconscious barrier. Some users might actually like it (it is distinctive), others will find it unprofessional.

**Decision**: `DROP` — Personal tool, owner's theme preference

---

### U6: Preview is a Dead Iframe (MEDIUM)

**What it means**: The right panel shows a live preview of the HTML document, but it's completely non-interactive. Users can't click on an element to highlight it in code, can't see what changed after an edit, can't test how the page looks on mobile, and can't interact with buttons/forms in the preview.

**Implication**: For a visual document builder, the preview is read-only and passive. Users are working blind — they can see the output but can't interact with it in any meaningful way. This limits the tool to "generate and hope" rather than "generate and refine visually."

**Decision**: `DROP` — Iframe is already unsandboxed and interactive (tabs, buttons, forms all work)

---

### U7: Silent Failures / Poor Error Messages (MEDIUM)

**What it means**: Three issues bundled together:
1. When the document list fails to refresh, the error is silently swallowed — the user sees nothing, but the UI is now out of sync with the server
2. If the server goes down, users see "Failed to fetch" with no reconnection option
3. Server errors show raw HTTP codes ("500 Internal Server Error") instead of human-friendly messages

**Implication**: Users don't know when things go wrong, or when they do, the messages are unhelpful. They'll blame the tool when it "loses" their document (stale UI) or shows cryptic errors. Trust erodes.

**Decision**: `PROCEED` → Plan 021 Phase 4 (humanizeError + Toast component)

---

### U8: Export Lacks Progress Feedback (LOW)

**What it means**: When exporting to PDF, PPTX, or PNG, the only feedback is the word "Exporting..." for 15-30 seconds. No spinner, no progress bar, no step descriptions ("Rendering page...", "Generating slides..."). If the user glances away, they might miss the completion.

**Implication**: Users wonder if the export is stuck. They might click the button again, triggering duplicate exports. Minor annoyance but makes the tool feel unpolished.

**Decision**: `PROCEED` → Plan 021 Phase 4 (spinner + success message in dropdown)

---

### U9: Mobile Essentially Broken (LOW)

**What it means**: Responsive CSS exists, but on a phone the split-pane becomes a 50/50 vertical stack — both halves too small to use. Touch targets are too small. The tool is desktop-only in practice.

**Implication**: If your 2-5 users only use desktops, this doesn't matter. If anyone wants to check a document on their phone, they can't. Given the corporate desktop context, this is probably fine to defer.

**Decision**: `DROP` — Desktop-only tool

---

### U10: No Keyboard Shortcuts Reference (LOW)

**What it means**: The app has some keyboard shortcuts (Enter to send, Shift+Enter for newline, Escape to close modals) but they're not documented anywhere. No help panel, no shortcut overlay, no tooltip hints.

**Implication**: Power users won't discover shortcuts. New users have to guess. Minor friction.

**Decision**: `DROP` — Existing shortcuts (Enter, Shift+Enter, Escape) are intuitive enough

---

### U11: "ARCHITECT" AI Label (LOW)

**What it means**: AI responses are labeled "ARCHITECT" instead of "AI" or "Assistant." This is a cosmetic persona choice that adds no value for corporate users and may confuse them ("Is ARCHITECT a specific AI model? A feature tier?").

**Implication**: Minimal. Cosmetic confusion at worst. Easy fix (change one string).

**Decision**: `PROCEED` → Plan 021 Phase 4 (ARCHITECT → BUILDER)

---

### U12: Cancel Button Too Small During Streaming (LOW)

**What it means**: When the AI is generating a response, the send button turns into a small "Cancel" text button. For operations that take 30+ seconds, users want a big, unmissable stop button — not a tiny text label.

**Implication**: Users might not notice they can cancel, or might miss-click. Minor annoyance.

**Decision**: `DROP` — Current cancel button works fine

---

### U13: Template Preview Shows Technical Details (LOW)

**What it means**: When users preview a template before using it, they see the AI implementation instructions ("Fixed Sidebar: `<aside>` with nested `<ul>` navigation tree..."). Corporate users don't care about HTML tags — they want to see what the output looks like.

**Implication**: Templates feel technical and intimidating rather than inviting. Users who don't know HTML might be confused. But users who DO know HTML might actually find it useful.

**Decision**: `DROP` — Technical preview provides useful transparency for this audience

---

### U14: No Filename Input on Export (LOW)

**What it means**: The exported file name is auto-generated from the document title. Users can't customize it. If the document is "Untitled Document 3," that's the filename.

**Implication**: Users rename the file after downloading. Minor inconvenience.

**Decision**: `PROCEED` → Plan 021 Phase 4 (smarter auto-truncation, no filename input)

---

### U15: Infographic PNG-Only Not Explained (LOW)

**What it means**: For infographic documents, the PDF/PPTX/HTML export options are hidden with no explanation. Users see "Export" but only PNG is available. No tooltip explains why.

**Implication**: Users wonder why they can't export their infographic as PDF. They might think it's a bug. A simple tooltip ("Infographics are rendered as images — only PNG export is available") would fix this.

**Decision**: `PROCEED` → Plan 021 Phase 4 (inline text explanation in dropdown)

---

### U16: No Onboarding / Walkthrough (LOW)

**What it means**: When a new user opens the app for the first time, there's no explanation of what the tool does, no "getting started" guide, no sample output. The template cards help, but they assume the user already knows the workflow.

**Implication**: For your 2-5 users who you can train personally, this doesn't matter much. For any new user onboarding without you, they'll fumble for a few minutes.

**Decision**: `DEFER` — Wait for other enhancements to stabilize first

---

### U17: No "New Document" Button in Tabs (LOW)

**What it means**: The document tab bar shows existing documents but has no "+" button to create a new one. The only way to create a new document is by sending a chat message or using a template. Users coming from Chrome, VS Code, or any tabbed interface expect a "+" button.

**Implication**: Users might not realize they can have multiple documents in one session, or won't know how to create another one.

**Decision**: `PROCEED (with U1)` → No "+" button. Sessions = projects. Use "New Session" + session browser instead.

---

### U18: No Search in Chat History (LOW)

**What it means**: In a session with 50+ messages, there's no search/filter to find a previous request or response. Users have to scroll manually.

**Implication**: For long sessions, finding a specific message becomes tedious. Minor for short sessions.

**Decision**: `DROP` — Chat messages too terse to warrant search

---

### U19: Dead CSS Animations (LOW)

**What it means**: Three CSS animations (`conduit-sweep`, `conduit-pulse`, `status-beacon`) are defined in the theme file but never used anywhere. Dead code — leftover from a previous design iteration.

**Implication**: No functional impact. Just code clutter (~25 lines). Easy cleanup.

**Decision**: `PROCEED` → Plan 021 Phase 4 (dead CSS cleanup)

---

## Architecture Findings

### A1: ~130 Lines of Dead SVG Code (HIGH)

**What it means**: The image service still contains functions for generating SVG diagrams (flowcharts, charts, timelines). These were documented as "removed in Plan 015" but the code was never actually deleted. Nobody calls these functions — they're orphaned.

**Implication**: 130 lines of dead code that confuses anyone reading the file. No functional harm, but it gives a false impression that SVG generation is still a feature. Clean delete, zero risk.

**Decision**: `RESOLVED in Plan 020a`

---

### A2: Copy-Pasted Image Retry Logic (MEDIUM)

**What it means**: The image generation service and the infographic service both have nearly identical retry logic (~60 lines each) for calling the image AI model. Same structure: try primary → retry primary → try fallback. The code was copied from one to the other instead of being shared.

**Implication**: If we ever need to change retry behavior (add a third attempt, change timeout, add logging), we'd need to change it in two places and hope we don't forget one. Classic maintenance trap. But at 2 services, it's manageable.

**Decision**: `RESOLVED in Plan 020a`

---

### A3: Duplicated Utility Functions (MEDIUM)

**What it means**: Two helper functions (`_validate_html` for checking if HTML is valid, and `_generate_filename` for creating export filenames) exist as exact copies in two different files. Same code, two locations.

**Implication**: Same as A2 — changes need to happen in two places. Easy to forget one. Low risk at current scale but a code smell.

**Decision**: `RESOLVED in Plan 020a`

---

### A4: Providers Instantiated Per-Request (LOW)

**What it means**: Every time a user sends a chat message, the code creates brand new AI provider objects (Anthropic, Gemini), each with a fresh HTTP connection. It's like opening a new browser window for every Google search instead of reusing the same tab.

**Implication**: ~50-100ms extra latency per message and slightly more memory usage. Imperceptible for 2-5 users. The pattern was chosen deliberately for easier testing. Not worth fixing unless we scale significantly.

**Decision**: `RESOLVED in Plan 020a`

---

### A5: Silent Route Fallthrough (MEDIUM)

**What it means**: If the intent router produces an unexpected result (not "edit", "create", "image", or "infographic"), the code falls into an `else` branch that sends a "done" event with no content and no error. The user sees... nothing. No response, no error message, just silence.

**Implication**: Extremely unlikely to trigger (the router has explicit fallbacks), but if it ever does, the user gets zero feedback. A one-line fix to yield an error message instead.

**Decision**: `RESOLVED in Plan 020a`

---

### A6: Migration Error Swallowing (LOW)

**What it means**: When the database runs schema migrations (adding new columns), it catches ALL errors and silently ignores them. This is intentional — it catches "column already exists" errors so migrations can be re-run safely. But it also catches genuinely bad errors like "disk full" or "database corrupted," hiding them.

**Implication**: If a migration genuinely fails (not a duplicate column), we'd never know. The app would continue running with a broken schema. Low probability but high severity if it happens.

**Decision**: `RESOLVED in Plan 020a`

---

### A7: `assert` in Production Code (LOW)

**What it means**: Two places in the session service use Python's `assert` statement to check for unexpected null values. `assert` is a debugging tool — if Python is run with optimization flags (`-O`), all asserts are silently removed. The checks would disappear.

**Implication**: We don't use `-O` in production (Docker runs plain `python`), so this works today. But it's bad practice — if someone changes the Docker command or runs the code differently, these safety checks vanish. Easy fix: replace with `if/raise`.

**Decision**: `RESOLVED in Plan 020a`

---

### A8: No `.dockerignore` (LOW)

**What it means**: When Docker builds the image, it sends the entire project directory as "build context" — including `.git` history, test files, `node_modules`, `__pycache__`, implementation plans, etc. None of this is needed in the final image. It's like mailing someone a package but including all your drafts and scratch paper.

**Implication**: Slower Docker builds (more data to send), slightly larger intermediate layers. The final image is fine (multi-stage build discards extras), but the build process is slower than necessary.

**Decision**: `RESOLVED in Plan 020a`

---

### A9: Unpinned Requirements (LOW)

**What it means**: Python dependencies are specified as `>=0.111.0` (minimum version) instead of `==0.111.0` (exact version). This means running `pip install` today might install different versions than running it next month. Builds are not reproducible.

**Implication**: A future `pip install` could pull a breaking change in a dependency, causing the app to fail on a fresh deploy. Hasn't happened yet, but it's a time bomb. However, pinning versions mid-project requires careful testing — you need to verify the exact set works together.

**Decision**: `RESOLVED in Plan 020a`

---

### A10: Known Failing Test Never Fixed (LOW)

**What it means**: `test_tables_created` has been failing since Plan 011 (when the `templates` table was removed). The test still checks for a table that no longer exists. It's been documented as "known failure" for months but never fixed.

**Implication**: A perpetually failing test is worse than no test — it trains developers to ignore test failures. "Oh, that one always fails." Then a real failure gets ignored too. One-line fix: remove `templates` from the expected list.

**Decision**: `RESOLVED in Plan 020a`

---

### A11: `process_file` is Async But Blocks (LOW)

**What it means**: The file upload processor is declared as `async` (non-blocking) but internally does synchronous file I/O (reading PDFs, parsing DOCX, etc.). While it's processing a large file, the entire server is blocked — no other requests can be handled.

**Implication**: If someone uploads a 50MB PDF, all other users are frozen for a few seconds while it parses. With 2-5 users, the chance of overlap is low. But it violates the async contract.

**Decision**: `RESOLVED in Plan 020a`

---

### A12: Missing Traceback in Chat Error Logging (LOW)

**What it means**: When an error occurs during chat processing, the log captures the error message but not the full stack trace (missing `exc_info=True`). When debugging production issues, you'd see "Error: something broke" but not *where* it broke.

**Implication**: Makes debugging harder. You'd have to reproduce the error locally to find the source. One-line fix.

**Decision**: `RESOLVED in Plan 020a`

---

### A13: Inconsistent Type Annotation Style (LOW)

**What it means**: One file uses the old Python style `Optional[str]` while everything else uses the modern style `str | None`. Pure cosmetic inconsistency.

**Implication**: Zero functional impact. Just visual inconsistency for anyone reading the code.

**Decision**: `RESOLVED in Plan 020a`

---

### A14: Redundant Conditional in Export Service (LOW)

**What it means**: The export code checks `if format != "png": raise error`, then immediately checks `if format == "png": do stuff`. The second check is always true since the first one already excluded non-png. It's logically correct but reads oddly.

**Implication**: Zero functional impact. Just slightly confusing to read. Cosmetic cleanup.

**Decision**: `RESOLVED in Plan 020a`

---

### A15: Liskov Substitution Violation in Providers (LOW)

**What it means**: The `LLMProvider` base class defines a `generate_with_tools()` method. The Gemini provider inherits from it but throws a "not implemented" error if you try to call it. This means you can't safely swap in a Gemini provider anywhere the code expects a generic LLM provider — it might crash.

**Implication**: In practice, the code explicitly uses the Anthropic provider for tool-based editing and never passes Gemini where tools are needed. So this never actually fails. But it's an architectural smell — the base class promises something that one implementation can't deliver.

**Decision**: `RESOLVED in Plan 020a`

---

## Decision Summary

Workshop conducted February 2026. Decisions below. Items marked PROCEED are in **Plan 021**. Architecture items (A1-A15) were addressed in **Plan 020a** (already COMPLETE).

| Item | Decision | Plan/Phase |
|------|----------|------------|
| U1 | **PROCEED** | 021 Phase 1 (Auth) + Phase 2 (Session History) |
| U2 | DEFER | Low ROI for short prompts |
| U3 | **PROCEED** | 021 Phase 3 (Version Diff) |
| U4 | DEFER | |
| U5 | DROP | Personal theme preference |
| U6 | DROP | Iframe already interactive (no sandbox) |
| U7 | **PROCEED** | 021 Phase 4 (UX Polish) |
| U8 | **PROCEED** | 021 Phase 4 (UX Polish) |
| U9 | DROP | Desktop-only tool |
| U10 | DROP | Existing shortcuts intuitive enough |
| U11 | **PROCEED** | 021 Phase 4 (UX Polish) |
| U12 | DROP | Current cancel button is fine |
| U13 | DROP | Technical preview useful for this audience |
| U14 | **PROCEED** | 021 Phase 4 (UX Polish) |
| U15 | **PROCEED** | 021 Phase 4 (UX Polish) |
| U16 | DEFER | Wait for enhancements to stabilize |
| U17 | **PROCEED** (with U1) | 021 Phase 2 — No "+" button, use session browser instead |
| U18 | DROP | Chat messages too terse to warrant search |
| U19 | **PROCEED** | 021 Phase 4 (UX Polish) |
| A1-A15 | RESOLVED | All addressed in Plan 020a (COMPLETE) |
