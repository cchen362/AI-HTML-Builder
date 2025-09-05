# AI HTML Builder - Redesign Documentation

## Overview
Transforming the AI HTML Builder into a focused conversational HTML generation tool with real-time rendering and Claude Artifacts-style separation between conversation and generated content.

## Core Vision
The main strength of this app is rendering HTML content in real-time in the rendering panel. The redesign focuses on:
- **Conversational Experience**: Chat window for interaction and explanations
- **Artifacts-Style Separation**: HTML content renders in the panel, conversations in chat
- **Large Text Support**: Expandable input for copy-pasting large content
- **Creative Freedom**: Remove template restrictions for more compelling outputs

## Key Issues Addressed

### Current Problems
1. **Repetitive AI Responses**: Same generic messages regardless of request
2. **Small Query Field**: Fixed textarea that can't handle large text inputs
3. **File Upload Clutter**: Unnecessary file upload features
4. **Template Restrictions**: Bland, restrictive system prompts
5. **Mixed Output**: HTML and conversation not properly separated
6. **Missing Full Screen**: No way to view HTML in new tab

### Design Goals
- Support users copying/pasting large amounts of text or articles
- Real-time HTML rendering with clean separation
- Conversational AI responses for explanations and interactions  
- Professional, visually compelling HTML outputs
- Large context window for iterative improvements
- Maintain existing panel divider functionality

## Implementation Plan

### Phase 1: Frontend Enhancements

#### 1. Enhanced Chat Input (`ChatInput.tsx`)
- **REMOVE**: All file upload functionality
  - File upload button and icons
  - Drag/drop handlers and visual feedback
  - File input element and validation
  - Upload-related help text
- **ADD**: Expandable textarea
  - Dynamic height adjustment (up to 20-30% of chat panel)
  - Auto-resize based on content
  - Proper min/max constraints
- **PRESERVE**: Ctrl+Enter shortcut functionality

#### 2. Full Screen HTML Viewer (`App.tsx`)
- **ADD**: "Full Screen View" button next to Export
- **FUNCTIONALITY**: Open rendered HTML in new browser tab
- **PRESERVE**: Existing preview/code toggle and export features

#### 3. Conversational WebSocket Handling (`useWebSocket.ts`)
- **MODIFY**: Message handling for dual response architecture
  - `html_output`: Direct to rendering panel
  - `conversation`: Display in chat window as AI response
- **REMOVE**: Generic AI response generation on frontend
- **ENHANCE**: Support large context without truncation

#### 4. Better Message Display (`MessageList.tsx`)
- **IMPROVE**: Handle longer conversational responses
- **ENHANCE**: Meaningful progress indicators during generation

### Phase 2: Backend Architecture Changes

#### 5. Creative System Prompt (`llm_service.py`)
- **REPLACE**: Template-heavy system prompt
- **IMPLEMENT**: UI/UX designer-focused approach using Extended Developer prompt
- **FOCUS**: Professional, creative single-file HTML/CSS/JS generation
- **REMOVE**: All predefined template methods and restrictions

#### 6. Dual Response Architecture
- **MODIFY**: WebSocket responses to send both outputs:
  ```json
  {
    "type": "update",
    "payload": {
      "html_output": "<!DOCTYPE html>...", // Pure HTML for rendering
      "conversation": "I've created a modern landing page with..."  // Chat response
    }
  }
  ```

#### 7. Large Context Support
- **INCREASE**: Context window limits for large text inputs
- **IMPROVE**: Handling of iterative changes without full rewrites
- **IMPLEMENT**: Smart context management for incremental modifications

#### 8. Remove Upload Functionality
- **DISABLE**: Upload endpoints in `upload.py`
- **REMOVE**: File processing service integration
- **CLEAN**: Unused file processing code

### Phase 3: LLM Enhancement

#### 9. Enhanced System Prompt Strategy
```markdown
You are an expert UI/UX designer and HTML architect with exceptional taste who specializes in creating professional, visually compelling single-file HTML/CSS/Javascript content.

DUAL OUTPUT REQUIREMENTS:
1. HTML_OUTPUT: Complete, production-ready HTML file (no explanations)
2. CONVERSATION: Friendly explanation of what you created and why

Brand Colors: Bright Blue #0066CF, Light Blue #66A9E2, Deep Blue #00175A, etc.
[Full brand guidelines from AI_HTML_Builder_Prompts.md]

Focus on creativity, visual appeal, and user requirements while maintaining professionalism.
```

#### 10. Incremental Change Handling
- **IMPLEMENT**: Context-aware modifications
- **STRATEGY**: Change only requested portions, preserve existing structure
- **MAINTAIN**: Consistency across iterations

## Technical Specifications

### Frontend Changes
- **ChatInput**: Remove file handling, implement auto-expanding textarea
- **App**: Add full-screen viewer button with `window.open()`
- **WebSocket**: Handle dual response format
- **MessageList**: Better display for longer conversations

### Backend Changes
- **LLM Service**: New creative system prompt, dual output format
- **WebSocket Handler**: Send both HTML and conversation responses
- **API**: Remove/disable upload endpoints

### Preserved Elements
- ✅ Panel divider functionality (working perfectly)
- ✅ Preview/code toggle in HTML viewer
- ✅ Export functionality
- ✅ Session management and Redis integration
- ✅ WebSocket real-time communication

## Success Metrics
1. **UX Improvement**: Users can easily paste large text inputs
2. **Creative Output**: More visually compelling HTML generation
3. **Clean Separation**: HTML renders without conversation text
4. **Full Screen**: HTML can be viewed in dedicated tab
5. **Conversational**: AI provides helpful explanations in chat
6. **Iterative**: Changes modify specific portions without full rewrites

## Implementation Notes
- Maintain backward compatibility where possible
- Test with large text inputs (articles, documents)
- Ensure WebSocket stability with new message format
- Validate HTML output quality with new creative prompt
- Test incremental modification scenarios

---

**Status**: Ready for implementation  
**Priority**: High - Core functionality redesign  
**Timeline**: Immediate execution