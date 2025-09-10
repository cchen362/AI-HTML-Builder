# Manual Test Plan: Content Disappearing During Reiteration

## Test Environment
- Backend: http://localhost:8000 (running)
- Frontend: http://localhost:5177 (running)
- Services: Memory store (Redis fallback)
- API Key: Configured

## Test Steps

### Step 1: Generate Initial Comprehensive Content
1. Open browser to http://localhost:5177
2. Enter the following request in chat:

```
Create a comprehensive impact assessment report titled "Impact Assessment Report - Time Sensitive Case Management Solutions" with the following sections:

1. Problem Statement with detailed analysis of current challenges
2. Technical Solutions with multiple options and detailed comparisons  
3. Risk Analysis with identified issues and mitigation strategies
4. Recommendations with implementation timeline and next steps

Include tabbed navigation, professional blue styling, and make each section comprehensive with multiple paragraphs and detailed content.
```

3. **Wait for generation** - Should produce a full HTML page with substantial content
4. **Take screenshot** of the preview showing full content
5. **Verify content sections** - All 4 sections should be visible and populated
6. **Save HTML** - Export or copy the generated HTML for comparison

### Step 2: Request Modification (Trigger Surgical Editing)
1. In the same chat session, enter:

```
Remove the Option Comparison tab and keep the rest of the content and formatting
```

2. **Wait for response** - This should trigger surgical editing in the backend
3. **Take screenshot** of the result
4. **Compare with Step 1** - Check if content disappeared

### Expected Results if Hypothesis is Correct

**Step 1 Result:**
- Full HTML with comprehensive content in all sections
- Multiple paragraphs per section
- Complete tabbed interface
- Professional styling throughout

**Step 2 Result (Bug):**
- Only header/title visible: "Impact Assessment Report - Time Sensitive Case Management Solutions"  
- Body content missing or severely truncated
- Tabs may be missing or broken
- Matches the pattern seen in ai9.png screenshot

### What This Proves
If Step 2 shows content disappearing while Step 1 shows full content, this confirms:

1. **Surgical editing detection** triggered by modification words ("Remove")
2. **HTML context truncation** in `_prepare_html_for_context()` method  
3. **Incomplete HTML generation** due to malformed context
4. **Frontend receives truncated HTML** and displays only headers

### Backend Log Monitoring
During testing, monitor backend logs for:
- `[CLAUDE MESSAGES] Using surgical editing approach` 
- `Prepared HTML context for modification` with length information
- Any HTML truncation warnings
- Claude API call details and response lengths

### Alternative Test (If Step 2 Works)
If modification preserves content, try more aggressive triggers:
- "Change the blue color to green"  
- "Update the header text"
- "Modify the Risk Analysis section"

These should also trigger surgical editing path.

## Success Criteria
- **Reproduce Issue**: Step 2 shows content disappearing 
- **Identify Cause**: Backend logs show surgical editing and context truncation
- **Validate Hypothesis**: Surgical editing approach causes the content loss

This manual test avoids WebSocket programming issues and directly replicates the user experience described in the issue report.