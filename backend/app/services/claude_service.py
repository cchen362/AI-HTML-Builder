"""
Revolutionary Claude Sonnet 4 Service for High-Quality HTML Generation

This service uses Claude Sonnet 4's superior HTML/CSS generation capabilities
with simplified, trust-based prompts that deliver professional results.
"""

import anthropic
import re
import time
from typing import List, Dict, Any, Optional, NamedTuple
from datetime import datetime
import structlog
from bs4 import BeautifulSoup, NavigableString
import html
from ..core.config import settings

logger = structlog.get_logger()

class DualResponse(NamedTuple):
    """Structured response containing both HTML artifact and conversation"""
    html_output: str
    conversation: str
    metadata: Dict[str, Any]

class ClaudeService:
    """
    Revolutionary Claude Sonnet 4 service for superior HTML/CSS generation.
    Uses simplified prompts that trust Claude's inherent design capabilities.
    """
    
    def __init__(self):
        # Validate Anthropic API key
        anthropic_key = getattr(settings, 'anthropic_api_key', None)
        if not anthropic_key:
            logger.error("Anthropic API key not configured")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        if not anthropic_key.startswith('sk-ant-'):
            logger.error("Invalid Anthropic API key format")
            raise ValueError("Anthropic API key must start with 'sk-ant-'")
        
        self.client = anthropic.Anthropic(api_key=anthropic_key)
        self.model = "claude-sonnet-4-20250514"  # Latest Claude Sonnet 4
        
        logger.info("Claude Sonnet 4 service initialized", model=self.model)
        
    async def validate_connection(self) -> bool:
        """Test Claude API connection"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            logger.info("Claude API connection validated successfully")
            return True
        except Exception as e:
            logger.error("Claude API connection failed", error=str(e))
            return False

    def generate_dual_response(
        self, 
        user_input: str, 
        context: List[Dict[str, Any]], 
        session_id: str,
        color_scheme: str = "light"
    ) -> DualResponse:
        """
        Generate high-quality HTML and conversation using Claude Sonnet 4
        """
        logger.info("[DEBUG] Claude generate_dual_response method called!", session_id=session_id, user_input_length=len(user_input))
        try:
            # Build simple message structure with color scheme support
            system_prompt, messages = self._build_simple_messages(user_input, context, color_scheme)
            
            # Enhanced parameters for iterative editing and larger outputs
            max_tokens = 12000  # Increased for safety buffer with complex templates
            temperature = 0.7
            
            logger.info(
                "[CLAUDE API CALL] Generating with Claude Sonnet 4",
                model=self.model,
                input_length=len(user_input),
                context_messages=len(context),
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Check if semantic targeting was already performed
            if messages and len(messages) == 1 and messages[0].get("role") == "system":
                semantic_content = messages[0].get("content", "")
                semantic_match = re.search(r'\[SEMANTIC_RESULT\](.*?)\[/SEMANTIC_RESULT\]', semantic_content, re.DOTALL)
                
                if semantic_match:
                    html_output = semantic_match.group(1).strip()
                    logger.info(
                        "[SEMANTIC TARGETING] Used pre-generated result",
                        result_length=len(html_output)
                    )
                    # Create dummy response data for consistency
                    response_data = type('obj', (object,), {
                        'usage': type('obj', (object,), {
                            'input_tokens': 0,
                            'output_tokens': 0
                        })()
                    })()
                else:
                    # Normal Claude API call
                    response = self._call_claude_with_retry(system_prompt, messages, max_tokens, temperature)
                    response_data = response
                    
                    logger.info(
                        "[CLAUDE API RESPONSE] Received response from Claude",
                        response_length=len(response.content[0].text),
                        usage_tokens=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
                    )
                    
                    # Simple response parsing - expect pure HTML
                    html_output = self._parse_simple_response(response.content[0].text)
            else:
                # Normal Claude API call
                response = self._call_claude_with_retry(system_prompt, messages, max_tokens, temperature)
                response_data = response
                
                logger.info(
                    "[CLAUDE API RESPONSE] Received response from Claude",
                    response_length=len(response.content[0].text),
                    usage_tokens=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
                )
                
                # Simple response parsing - expect pure HTML
                html_output = self._parse_simple_response(response.content[0].text)
            conversation = self._generate_simple_conversation(html_output, user_input)
            
            # Generate metadata
            input_tokens = response_data.usage.input_tokens if response_data.usage else 0
            output_tokens = response_data.usage.output_tokens if response_data.usage else 0
            total_tokens = input_tokens + output_tokens
            
            metadata = {
                "model": self.model,
                "title": self._extract_title(html_output),
                "type": self._determine_type(html_output, user_input),
                "timestamp": datetime.utcnow().isoformat(),
                "version": 1,
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
            
            logger.info(
                "Claude response generated successfully",
                html_length=len(html_output),
                conversation_length=len(conversation),
                tokens_used=metadata["tokens_used"]
            )
            
            return DualResponse(
                html_output=html_output,
                conversation=conversation,
                metadata=metadata
            )
            
        except anthropic.AuthenticationError as e:
            logger.error("Claude authentication failed", error=str(e))
            return self._get_fallback_response(user_input, "Authentication error with Claude API.")
            
        except anthropic.RateLimitError as e:
            logger.error("Claude rate limit exceeded", error=str(e))
            return self._get_fallback_response(user_input, "I'm experiencing high demand. Please try again in a moment.")
            
        except Exception as e:
            logger.error("Claude generation failed", error=str(e), user_input_length=len(user_input))
            return self._get_fallback_response(user_input, "I encountered an issue generating your content. Please try again!")

    def _get_surgical_system_prompt(self, color_scheme: str = "light") -> str:
        """
        System prompt optimized for surgical HTML editing with color scheme awareness
        """
        color_preservation = ""
        if color_scheme == "dark":
            color_preservation = """
- Preserve existing dark mode @media queries and ensure any new elements include dark mode styling
- If adding new elements, include both light and dark mode CSS using @media (prefers-color-scheme: dark)
- Maintain existing color scheme support (user prefers dark mode)"""
        else:
            color_preservation = """
- Preserve any existing @media (prefers-color-scheme: dark) rules
- If adding new elements, include basic dark mode support for consistency
- Maintain existing light mode appearance while ensuring dark mode compatibility"""

        return f"""You are an expert HTML/CSS designer specializing in PRECISE, TARGETED modifications to existing HTML documents.

CRITICAL PRESERVATION RULE:
🚨 PRESERVE EVERYTHING EXCEPT WHAT IS EXPLICITLY REQUESTED TO CHANGE 🚨

SURGICAL EDITING APPROACH:
- Make ONLY the specific, targeted changes requested - nothing more, nothing less
- Treat the existing document as sacred - preserve all content, structure, styling, and functionality
- If user says "keep everything the same but change X" - keep EVERYTHING except X
- If user says "preserve the formatting" - maintain ALL existing styling
- Never recreate or restructure existing content unless explicitly asked
{color_preservation}

MODIFICATION GUIDELINES:
1. IDENTIFY PRECISELY what needs to change (e.g., "just the header title", "only the pricing section")
2. LOCATE the exact HTML element(s) that contain what needs to change
3. MODIFY only those specific elements while keeping everything else identical
4. PRESERVE all existing CSS classes, IDs, structure, and JavaScript
5. MAINTAIN all interactive elements (tabs, buttons, navigation) exactly as they were
6. KEEP all existing content, text, images, and layout intact

ABSOLUTE PRESERVATION REQUIREMENTS:
- All existing text content (unless specifically changing that text)
- All existing HTML structure and element hierarchy  
- All existing CSS styling and classes
- All existing JavaScript functionality
- All existing responsive behavior
- All existing color schemes and themes
- All existing animations and transitions

BRAND CONSISTENCY:
- Use existing colors, typography, and design patterns already in the document
- Match existing spacing, layout, and visual hierarchy exactly
- Maintain the same professional appearance and quality level

OUTPUT REQUIREMENTS:
- Return ONLY the complete modified HTML document
- No explanations or additional text
- Changes should be seamlessly integrated and undetectable except for the requested modification
- Document should look and behave exactly the same except for the specific change requested"""

    def _get_simple_system_prompt(self, color_scheme: str = "light") -> str:
        """
        Enhanced system prompt that supports both new creation and iterative editing with color scheme awareness
        """
        # Define color scheme specific instructions
        color_instructions = ""
        if color_scheme == "dark":
            color_instructions = """
DARK MODE OPTIMIZED: The user prefers dark mode. Generate HTML that automatically adapts to both light and dark color schemes using CSS media queries:

CSS REQUIREMENTS:
- Include @media (prefers-color-scheme: dark) rules for all styling
- Dark mode backgrounds: #1a1a1a, #2d2d2d, #3a3a3a (instead of white/light gray)
- Dark mode text: #e0e0e0, #ffffff (instead of dark colors)
- Dark mode borders: #404040, #555 (instead of light gray)
- Keep brand blues (#003366, #0066CF) with proper contrast adjustments for dark mode
- Ensure all elements have both light and dark mode styling

EXAMPLE PATTERN:
```css
.container {
  background: white;
  color: #333;
}
@media (prefers-color-scheme: dark) {
  .container {
    background: #2d2d2d;
    color: #e0e0e0;
  }
}
```"""
        else:
            color_instructions = """
LIGHT MODE OPTIMIZED: Generate HTML with professional light mode styling, but include basic dark mode support using @media (prefers-color-scheme: dark) queries for future compatibility."""

        return f"""You are an expert HTML/CSS designer who creates and modifies professional single-file HTML documents.

For NEW requests: Create a complete, production-ready HTML file with:
- All CSS inline in <style> tags with dual light/dark mode support
- All JavaScript inline in <script> tags (if needed)  
- Mobile-responsive design
- Professional appearance using blue (#003366, #0066CF), white, and grey brand colors
- Clean, minimal UI elements
- Modern design principles
{color_instructions}

For MODIFICATION requests: Update the existing HTML while preserving:
- Overall structure and design consistency
- Brand colors and styling approach  
- Responsive behavior
- All inline CSS/JS approach
- Any interactive elements (tabs, buttons, etc.)
- Existing color scheme support (light/dark mode)

IMPORTANT: 
- Always return ONLY the complete HTML document starting with <!DOCTYPE html>
- No explanations, markdown formatting, or additional text
- Ensure all modifications integrate seamlessly with existing design
- Maintain professional quality throughout
- Always include @media (prefers-color-scheme: dark) rules for comprehensive color scheme support"""

    def _build_simple_messages(self, user_input: str, context: List[Dict[str, Any]], color_scheme: str = "light") -> tuple[str, List[Dict[str, str]]]:
        """Build message structure with intelligent surgical editing and fallback logic"""
        
        # Detect if this is a modification request
        modification_words = ["change", "modify", "update", "adjust", "fix", "edit", "improve", "enhance", "make", "add", "remove", "alter", "delete"]
        is_modification = any(word in user_input.lower() for word in modification_words)
        
        # Enhanced decision logic for surgical editing
        should_use_surgical_editing = (
            is_modification and 
            context and 
            len(context) > 0 and
            self._should_attempt_surgical_editing(context, user_input)
        )
        
        # Enhanced logging for decision tracking
        logger.info("[DECISION TRACKING] Message approach analysis",
                   user_input_preview=user_input[:100],
                   is_modification=is_modification,
                   has_context=len(context) > 0 if context else False,
                   context_messages=len(context) if context else 0,
                   should_use_surgical=should_use_surgical_editing,
                   color_scheme=color_scheme)
        
        if should_use_surgical_editing:
            try:
                # Find the current HTML document for semantic targeting
                last_html = None
                for msg in reversed(context):
                    if msg.get("sender") == "assistant" and msg.get("html_output"):
                        last_html = msg["html_output"]
                        break
                
                if last_html:
                    logger.info("[CLAUDE MESSAGES] ✅ SURGICAL EDITING SELECTED - Using semantic targeting", 
                               html_size=len(last_html),
                               modification_detected=True,
                               approach="semantic_targeting")
                    
                    # Perform semantic targeting edit directly
                    system_prompt = self._get_surgical_system_prompt(color_scheme)
                    modified_html = self._perform_semantic_targeting_edit(user_input, last_html, system_prompt)
                    
                    # Return special flag to indicate semantic targeting was used
                    messages = [{"role": "system", "content": f"[SEMANTIC_RESULT]{modified_html}[/SEMANTIC_RESULT]"}]
                    return system_prompt, messages
                else:
                    logger.warning("No HTML found for surgical editing, falling back to creation")
            except Exception as e:
                logger.warning("[CLAUDE MESSAGES] ⚠️ Surgical editing failed, falling back to creation", error=str(e))
                # Fall through to creation approach
        
        # Use creation approach (either by choice or fallback)
        system_prompt = self._get_simple_system_prompt(color_scheme)
        messages = self._build_creation_messages(user_input, context)
        fallback_reason = "surgical_editing_failed" if should_use_surgical_editing else "new_content_creation"
        logger.info("[CLAUDE MESSAGES] 🆕 CREATION MODE SELECTED", 
                   message_count=len(messages), 
                   modification_detected=is_modification,
                   fallback_reason=fallback_reason,
                   approach="full_generation")
        
        return system_prompt, messages

    def _should_attempt_surgical_editing(self, context: List[Dict[str, Any]], user_input: str) -> bool:
        """Simplified decision logic: use surgical editing for any modification request with existing HTML"""
        try:
            # Find the most recent HTML content
            last_html = None
            for msg in reversed(context):
                if msg.get("sender") == "assistant" and msg.get("html_output"):
                    last_html = msg["html_output"]
                    break
            
            if not last_html:
                logger.info("No previous HTML found, using creation mode")
                return False
            
            # Check for modification keywords (much more comprehensive)
            modification_words = [
                "change", "modify", "update", "adjust", "fix", "edit", "improve", "enhance",
                "make", "add", "remove", "alter", "delete", "replace", "keep", "preserve", 
                "maintain", "but", "except", "only", "just", "hide", "show", "color", 
                "text", "title", "content", "section", "tab", "header", "footer"
            ]
            
            # Check for preservation keywords (strong indicators)
            preservation_words = [
                "keep", "preserve", "maintain", "same", "but", "except", "only", "just"
            ]
            
            request_lower = user_input.lower()
            has_modification = any(word in request_lower for word in modification_words)
            has_preservation = any(word in request_lower for word in preservation_words)
            
            # Use surgical editing if:
            # 1. Any modification keyword detected, OR
            # 2. Strong preservation indicators
            should_use = has_modification or has_preservation
            
            logger.info("Surgical editing decision (simplified)", 
                       should_use=should_use,
                       has_modification=has_modification,
                       has_preservation=has_preservation,
                       html_size=len(last_html),
                       request_preview=user_input[:100])
            
            return should_use
            
        except Exception as e:
            logger.warning("Error in surgical editing decision logic", error=str(e))
            return False

    # Note: _build_surgical_edit_messages method removed - semantic targeting now handled in main flow

    def _perform_semantic_targeting_edit(self, user_input: str, last_html: str, system_prompt: str) -> str:
        """
        Semantic targeting approach inspired by Claude Artifacts.
        Identifies what needs to change, extracts relevant sections, modifies them, and merges back.
        """
        logger.info("Starting semantic targeting edit")
        
        try:
            # Phase 1: Identify what needs to change
            analysis_prompt = f"""Analyze this HTML document and user request to identify exactly what sections need modification.

HTML Document Length: {len(last_html)} characters

User Request: "{user_input}"

Please identify:
1. Which specific HTML elements/sections need to be modified
2. What type of change is needed (content, styling, structure)
3. Can this be done with targeted edits or does it require full recreation?

Respond with:
- TARGET_SECTIONS: List the specific elements (by class/id/tag) that need changes
- CHANGE_TYPE: content|styling|structure|addition|removal
- APPROACH: targeted|full_recreation
- REASONING: Brief explanation

Be precise - we want to preserve as much of the existing document as possible."""

            # Get analysis from Claude
            analysis_response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                system="You are an expert HTML analyst. Be precise and concise.",
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            analysis = analysis_response.content[0].text
            logger.info("Semantic analysis completed", analysis_length=len(analysis))
            
            # Phase 2: Determine approach based on analysis
            if "APPROACH: full_recreation" in analysis:
                logger.info("Analysis recommends full recreation, using standard approach")
                # Fall back to standard surgical editing
                return self._perform_standard_surgical_edit(user_input, last_html, system_prompt)
            
            # Phase 3: Extract target sections for targeted editing
            if "APPROACH: targeted" in analysis:
                return self._perform_targeted_section_edit(user_input, last_html, system_prompt, analysis)
            
            # Default fallback
            logger.warning("Semantic analysis unclear, using standard surgical edit")
            return self._perform_standard_surgical_edit(user_input, last_html, system_prompt)
            
        except Exception as e:
            logger.error("Semantic targeting failed, falling back to standard approach", error=str(e))
            return self._perform_standard_surgical_edit(user_input, last_html, system_prompt)

    def _perform_targeted_section_edit(self, user_input: str, last_html: str, system_prompt: str, analysis: str) -> str:
        """Perform targeted edits on specific sections identified by semantic analysis"""
        try:
            # Enhanced prompt for targeted editing
            targeted_prompt = f"""You are performing TARGETED SECTION EDITING based on this analysis:

{analysis}

CRITICAL INSTRUCTIONS:
1. Make ONLY the changes identified in the analysis
2. Preserve ALL other content exactly as it exists
3. Focus on the specific sections mentioned in TARGET_SECTIONS
4. Do not recreate or restructure anything not mentioned

Current HTML Document:
{last_html[:120000]}  # Use our increased context limit

User Request: "{user_input}"

Return the COMPLETE modified HTML document with only the targeted changes applied."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=12000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": targeted_prompt}]
            )
            
            result = response.content[0].text.strip()
            logger.info("Targeted section edit completed", result_length=len(result))
            return result
            
        except Exception as e:
            logger.error("Targeted section edit failed", error=str(e))
            return self._perform_standard_surgical_edit(user_input, last_html, system_prompt)

    def _perform_standard_surgical_edit(self, user_input: str, last_html: str, system_prompt: str) -> str:
        """Standard surgical edit approach with full context"""
        try:
            # Prepare HTML context using our enhanced limits
            html_context = self._prepare_html_for_context(last_html)
            
            surgical_prompt = f"""Current HTML document to modify:

```html
{html_context}
```

User Request: "{user_input}"

Make the requested changes while preserving everything else exactly as it exists."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=12000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": surgical_prompt}]
            )
            
            result = response.content[0].text.strip()
            logger.info("Standard surgical edit completed", result_length=len(result))
            return result
            
        except Exception as e:
            logger.error("Standard surgical edit failed", error=str(e))
            raise

    def _build_creation_messages(self, user_input: str, context: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Build messages for new HTML creation"""
        messages = []
        
        # Include limited conversation history for context (last 2 exchanges)
        if context and len(context) > 0:
            conversation_pairs = []
            for i in range(len(context) - 1, -1, -1):
                msg = context[i]
                if msg.get("sender") == "user":
                    for j in range(i + 1, len(context)):
                        if context[j].get("sender") == "assistant":
                            user_content = msg.get("content", "")
                            assistant_content = context[j].get("conversation", "I created a design for you.")
                            conversation_pairs.insert(0, (user_content, assistant_content))
                            break
                
                if len(conversation_pairs) >= 2:  # Reduced from 3 to 2 for efficiency
                    break
            
            # Add conversation history
            for user_msg, assistant_msg in conversation_pairs:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
        
        # Add current request
        messages.append({"role": "user", "content": user_input})
        
        return messages

    def _parse_simple_response(self, response_text: str) -> str:
        """Enhanced parsing - handles both standard Claude responses and semantic targeting results"""
        try:
            response_text = response_text.strip()
            
            # Check for semantic targeting result first
            semantic_match = re.search(r'\[SEMANTIC_EDIT_RESULT\](.*?)\[/SEMANTIC_EDIT_RESULT\]', response_text, re.DOTALL)
            if semantic_match:
                semantic_html = semantic_match.group(1).strip()
                logger.info("[CLAUDE PARSE] Found semantic targeting result", length=len(semantic_html))
                
                # Validate it's proper HTML
                if semantic_html.startswith('<!DOCTYPE html>') or semantic_html.lower().startswith('<html'):
                    return semantic_html
                else:
                    # Try to extract HTML from within the semantic result
                    doctype_match = re.search(r'<!DOCTYPE html>.*?</html>', semantic_html, re.DOTALL | re.IGNORECASE)
                    if doctype_match:
                        return doctype_match.group(0)
            
            # Standard HTML parsing for direct Claude responses
            if response_text.startswith('<!DOCTYPE html>'):
                logger.info("[CLAUDE PARSE] Found clean HTML response")
                return response_text
            
            # Look for HTML content in the response
            doctype_match = re.search(r'<!DOCTYPE html>.*?</html>', response_text, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                html_content = doctype_match.group(0)
                logger.info("[CLAUDE PARSE] Extracted HTML from response")
                return html_content
            
            # If no proper HTML found, create a professional fallback
            logger.warning("[CLAUDE PARSE] No valid HTML found in response, creating fallback")
            return self._create_fallback_html("Could not parse Claude response")
            
        except Exception as e:
            logger.error("[CLAUDE PARSE] Failed to parse response", error=str(e))
            return self._create_fallback_html("Parse error occurred")
    
    def _prepare_html_for_context(self, html_content: str) -> str:
        """
        Senior-level HTML context preparation with structure integrity preservation.
        Uses intelligent DOM parsing and progressive content reduction.
        """
        if not html_content:
            return "No HTML content available."
        
        try:
            # Modern token limits - Claude Sonnet 4 can handle much more context
            MAX_HTML_CONTEXT_LENGTH = 150000  # Utilize 75% of Claude Sonnet 4's context window
            OPTIMAL_CONTEXT_LENGTH = 120000   # Target for performance with 15-iteration sessions
            
            # If content fits comfortably, return as-is
            if len(html_content) <= OPTIMAL_CONTEXT_LENGTH:
                logger.info("HTML context fits within optimal size", 
                           length=len(html_content))
                return html_content
            
            # Parse HTML with BeautifulSoup for proper DOM handling
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Create a structure-preserving context
            context_soup = self._create_structure_preserving_context(
                soup, MAX_HTML_CONTEXT_LENGTH
            )
            
            # Convert back to string
            context_html = str(context_soup)
            
            # Validate the result is well-formed HTML
            if not self._is_valid_html_structure(context_html):
                logger.warning("Generated context has structural issues, using fallback")
                return self._fallback_html_preparation(html_content, MAX_HTML_CONTEXT_LENGTH)
            
            logger.info("Prepared HTML context with structure preservation", 
                       original_length=len(html_content), 
                       context_length=len(context_html),
                       compression_ratio=f"{len(context_html)/len(html_content)*100:.1f}%")
            
            return context_html
        
        except Exception as e:
            logger.warning("Advanced HTML context preparation failed", error=str(e))
            return self._fallback_html_preparation(html_content, 150000)

    def _create_structure_preserving_context(self, soup: BeautifulSoup, max_length: int) -> BeautifulSoup:
        """
        Create a new BeautifulSoup object with critical structure preserved
        and content intelligently reduced to fit within token limits.
        """
        # Create new soup with basic structure
        new_soup = BeautifulSoup('<!DOCTYPE html><html><head></head><body></body></html>', 'lxml')
        new_html = new_soup.find('html')
        new_head = new_soup.find('head')
        new_body = new_soup.find('body')
        
        # 1. Preserve critical head elements
        original_head = soup.find('head')
        if original_head:
            # Copy essential head elements
            for tag_name in ['title', 'meta']:
                for tag in original_head.find_all(tag_name):
                    new_head.append(tag.extract() if tag.parent else tag)
            
            # Handle style tags with compression
            for style in original_head.find_all('style'):
                compressed_style = self._compress_css(style.string or '')
                if compressed_style:
                    new_style = new_soup.new_tag('style')
                    new_style.string = compressed_style
                    new_head.append(new_style)
        
        # 2. Preserve body structure with intelligent content reduction
        original_body = soup.find('body')
        if original_body:
            # Copy body attributes
            if original_body.attrs:
                new_body.attrs.update(original_body.attrs)
            
            # Progressive content addition with size monitoring
            current_length = len(str(new_soup))
            budget_remaining = max_length - current_length - 1000  # Reserve 1000 chars for closing tags
            
            # Priority order for content preservation
            content_priorities = [
                ('.container', 'main container'),
                ('.header', 'page header'),
                ('.tab-container', 'tab interface'),
                ('.tab-nav', 'tab navigation'),
                ('.tab-content', 'tab content sections'),
                ('h1, h2, h3', 'headings'),
                ('.section-title', 'section titles'),
                ('.subsection', 'subsections'),
                ('.metrics-grid', 'metrics'),
                ('.timeline', 'timeline elements'),
                ('script', 'javascript functionality')
            ]
            
            for selector, description in content_priorities:
                if budget_remaining <= 500:  # Stop if budget too low
                    logger.info(f"Budget exhausted, stopping at {description}")
                    break
                
                elements = original_body.select(selector)
                for element in elements:
                    element_html = str(element)
                    element_length = len(element_html)
                    
                    if element_length <= budget_remaining:
                        # Element fits, add it
                        new_element = BeautifulSoup(element_html, 'lxml').find()
                        if new_element:
                            new_body.append(new_element)
                            budget_remaining -= element_length
                            logger.debug(f"Added {description} element ({element_length} chars)")
                    else:
                        # Element too large, try to include a representative sample
                        sample = self._create_representative_sample(element, budget_remaining - 200)
                        if sample:
                            new_body.append(sample)
                            budget_remaining -= len(str(sample))
                            logger.debug(f"Added sampled {description} ({len(str(sample))} chars)")
        
        return new_soup
    
    def _compress_css(self, css_content: str) -> str:
        """Compress CSS while maintaining functionality"""
        if not css_content:
            return ""
        
        # Basic CSS minification
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove excessive whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        
        # Remove spaces around specific characters
        css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
        
        return css_content.strip()
    
    def _create_representative_sample(self, element, max_size: int) -> Optional[BeautifulSoup]:
        """Create a representative sample of a large element"""
        if max_size < 100:  # Too small to be useful
            return None
        
        try:
            # Create a simplified version with key attributes
            tag_name = element.name
            new_soup = BeautifulSoup('', 'lxml')
            sample_element = new_soup.new_tag(tag_name)
            
            # Copy important attributes
            if element.attrs:
                for attr, value in element.attrs.items():
                    if attr in ['class', 'id', 'data-*']:
                        sample_element[attr] = value
            
            # Add a representative content sample
            text_content = element.get_text(strip=True)
            if text_content:
                sample_text = text_content[:max_size//2] + "... [content truncated for context]"
                sample_element.string = sample_text
            
            return sample_element
        except Exception as e:
            logger.debug(f"Failed to create representative sample: {e}")
            return None
    
    def _is_valid_html_structure(self, html_content: str) -> bool:
        """Validate that HTML has proper structure for surgical editing"""
        try:
            # Check for essential structural elements
            required_elements = ['<!DOCTYPE', '<html', '<head', '<body']
            for element in required_elements:
                if element not in html_content:
                    return False
            
            # Basic tag balance check for critical tags
            critical_tags = ['html', 'head', 'body', 'div']
            for tag in critical_tags:
                open_count = html_content.count(f'<{tag}')
                close_count = html_content.count(f'</{tag}>')
                # Allow some imbalance due to self-closing or truncated content
                if abs(open_count - close_count) > 2:
                    logger.debug(f"Tag balance issue with {tag}: {open_count} opens, {close_count} closes")
                    return False
            
            return True
        except Exception as e:
            logger.debug(f"HTML validation failed: {e}")
            return False
    
    def _fallback_html_preparation(self, html_content: str, max_length: int) -> str:
        """Fallback method using simple truncation with structure preservation"""
        logger.info("Using fallback HTML preparation method")
        
        if len(html_content) <= max_length:
            return html_content
        
        try:
            # Find a safe truncation point (after a closing tag)
            truncate_point = max_length
            
            # Look backwards for a safe closing tag
            for i in range(max_length - 1, max_length - 500, -1):
                if i < len(html_content) and html_content[i] == '>' and html_content[i-1] != '/':
                    # Check if this looks like a closing tag
                    tag_start = html_content.rfind('<', max(0, i-50), i)
                    if tag_start != -1 and html_content[tag_start:tag_start+2] == '</':
                        truncate_point = i + 1
                        break
            
            truncated = html_content[:truncate_point]
            
            # Ensure we have proper closing tags
            if '</body>' not in truncated:
                truncated += '\n</body>'
            if '</html>' not in truncated:
                truncated += '\n</html>'
            
            logger.info("Applied fallback truncation", 
                       original_length=len(html_content),
                       truncated_length=len(truncated))
            
            return truncated
            
        except Exception as e:
            logger.warning(f"Fallback truncation failed: {e}")
            # Last resort: simple truncation
            return html_content[:max_length] + "\n... [HTML truncated]"

    def _summarize_html_structure(self, html_content: str) -> str:
        """Create a concise summary of HTML structure for context"""
        if not html_content:
            return "No previous HTML structure available."
        
        try:
            # Extract key structural elements
            title = self._extract_title(html_content)
            
            # Count major sections
            section_count = len(re.findall(r'<(section|div class="[^"]*section[^"]*"|article|main)', html_content, re.IGNORECASE))
            
            # Check for key features
            has_nav = '<nav' in html_content.lower() or 'navbar' in html_content.lower()
            has_header = '<header' in html_content.lower()
            has_footer = '<footer' in html_content.lower()
            has_tabs = 'tab' in html_content.lower() and ('onclick' in html_content.lower() or 'javascript' in html_content.lower())
            has_grid = 'display: grid' in html_content.lower() or 'grid-template' in html_content.lower()
            has_gradients = 'gradient' in html_content.lower()
            
            # Extract color scheme
            blue_colors = re.findall(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', html_content)
            primary_colors = [color for color in blue_colors if '003366' in color or '0066CF' in color or '4A90E2' in color]
            
            # Build summary
            features = []
            if has_nav: features.append("navigation menu")
            if has_header: features.append("header section")
            if has_tabs: features.append("interactive tabs")
            if has_grid: features.append("CSS Grid layout")
            if has_gradients: features.append("gradient backgrounds")
            if section_count > 0: features.append(f"{section_count} main sections")
            if primary_colors: features.append("blue brand color scheme")
            
            feature_text = ", ".join(features[:6])  # Limit to avoid token bloat
            
            return f"Current page: '{title}' with {feature_text}."
        
        except Exception as e:
            logger.warning("Failed to summarize HTML structure", error=str(e))
            title = self._extract_title(html_content) 
            return f"Current page: '{title}' (analysis unavailable)."

    def _generate_simple_conversation(self, html_output: str, user_input: str) -> str:
        """Generate simple conversation response about the created HTML"""
        title = self._extract_title(html_output)
        
        # Simple, consistent conversation response
        if "assessment" in user_input.lower():
            return f"I've created a professional impact assessment titled '{title}' with modern design, tabbed navigation, and your brand colors. The layout uses CSS Grid for clean organization and includes interactive elements for better user experience."
        elif "landing" in user_input.lower():
            return f"I've designed a modern landing page '{title}' with compelling visuals, clear call-to-actions, and responsive layout optimized for conversions."
        else:
            return f"I've created a professional webpage '{title}' with clean design, responsive layout, and modern styling that follows best practices for user experience."

    def _call_claude_with_retry(self, system_prompt: str, messages: List[Dict], max_tokens: int, temperature: float, max_retries: int = 3):
        """Call Claude API with exponential backoff retry and prompt caching"""
        for attempt in range(max_retries):
            try:
                # Check if messages contain cache control (indicates surgical editing)
                has_cache_control = any(
                    isinstance(msg.get("content"), list) and 
                    any(isinstance(content, dict) and content.get("cache_control") for content in msg["content"])
                    for msg in messages
                )
                
                # Prepare extra headers for prompt caching if needed
                extra_headers = {}
                if has_cache_control:
                    extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"
                    logger.info("[PROMPT CACHING] Using prompt caching for surgical editing")
                
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    extra_headers=extra_headers
                )
            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1.0
                    logger.info(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    logger.warning(f"Request failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    continue
                raise

    def _parse_response_old(self, response_text: str) -> tuple[str, str]:
        """Parse Claude's response to extract HTML and conversation"""
        try:
            # Try multiple parsing strategies
            
            # Strategy 1: Look for **HTML:** followed by code block
            html_pattern_1 = r'\*\*HTML:\*\*\s*\n```html\s*\n(.*?)\n```'
            html_match_1 = re.search(html_pattern_1, response_text, re.DOTALL | re.IGNORECASE)
            
            # Strategy 2: Look for **HTML:** without code block
            html_pattern_2 = r'\*\*HTML:\*\*\s*\n(.*?)(?=\n\s*\*\*CONVERSATION:\*\*|$)'
            html_match_2 = re.search(html_pattern_2, response_text, re.DOTALL | re.IGNORECASE)
            
            # Strategy 3: Look for any HTML content
            doctype_pattern = r'<!DOCTYPE html>.*?</html>'
            doctype_match = re.search(doctype_pattern, response_text, re.DOTALL | re.IGNORECASE)
            
            # Try conversation extraction
            conv_match = re.search(r'\*\*CONVERSATION:\*\*\s*\n(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            
            html_output = None
            conversation = None
            
            # Extract HTML using best strategy
            if html_match_1:
                html_output = self._clean_html(html_match_1.group(1).strip())
                logger.info("Used HTML parsing strategy 1 (code block)")
            elif html_match_2:
                html_output = self._clean_html(html_match_2.group(1).strip())
                logger.info("Used HTML parsing strategy 2 (direct)")
            elif doctype_match:
                html_output = self._clean_html(doctype_match.group(0))
                logger.info("Used HTML parsing strategy 3 (DOCTYPE search)")
            
            # Extract conversation
            if conv_match:
                conversation = conv_match.group(1).strip()
                logger.info("Found conversation in response")
            else:
                # Generate conversation from context clues
                conversation = self._generate_conversation_from_html(html_output, response_text)
                logger.info("Generated conversation from HTML context")
            
            # Validate HTML
            if html_output and (html_output.startswith('<!DOCTYPE html>') or 
                               html_output.lower().startswith('<html')):
                logger.info("Successfully parsed HTML and conversation", 
                           html_length=len(html_output), 
                           conversation_length=len(conversation))
                return html_output, conversation
            
            # If we got here, parsing failed
            logger.warning("HTML parsing failed - using fallback")
            return self._create_fallback_html("Could not parse Claude response"), "I had trouble parsing that response. Let me try a different approach."
            
        except Exception as e:
            logger.error("Failed to parse Claude response", error=str(e))
            return self._create_fallback_html("Parse error"), "I encountered a parsing error. Please try again with your request."

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content"""
        if not html_content:
            return html_content
        
        # Remove code block markers if present
        html_content = re.sub(r'```html\s*', '', html_content)
        html_content = re.sub(r'\s*```$', '', html_content)
        
        # Ensure starts with DOCTYPE
        html_content = html_content.strip()
        if not html_content.startswith('<!DOCTYPE'):
            doctype_match = re.search(r'<!DOCTYPE html>.*', html_content, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                html_content = doctype_match.group(0)
        
        return html_content.strip()

    def _extract_conversation(self, text: str) -> str:
        """Extract meaningful conversation from text"""
        # Remove common prefixes
        text = re.sub(r'^(CONVERSATION:|\*\*CONVERSATION:\*\*)', '', text, flags=re.IGNORECASE).strip()
        
        # Take first meaningful paragraph
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 20]
        return paragraphs[0] if paragraphs else "I've created a professional design tailored to your requirements."

    def _generate_conversation_from_html(self, html_content: str, full_response: str) -> str:
        """Generate conversation when no explicit conversation is provided"""
        if not html_content:
            return "I've created a professional webpage with modern design and responsive layout."
        
        # Extract key features from HTML
        title = self._extract_title(html_content)
        has_animations = 'transition:' in html_content.lower() or 'animation' in html_content.lower()
        has_grid = 'display: grid' in html_content.lower() or 'grid-template' in html_content.lower()
        has_gradients = 'gradient' in html_content.lower()
        is_complex = len(html_content) > 8000
        
        # Look for any text after HTML that might be conversational
        html_end = full_response.rfind('</html>')
        if html_end != -1:
            after_html = full_response[html_end + 7:].strip()
            if after_html and len(after_html) > 30 and not after_html.startswith('<'):
                # Clean up any formatting
                after_html = re.sub(r'```+', '', after_html).strip()
                if after_html:
                    return after_html[:300]  # Limit length
        
        # Generate contextual conversation
        features = []
        if has_gradients:
            features.append("gradient backgrounds")
        if has_grid:
            features.append("CSS Grid layout")
        if has_animations:
            features.append("smooth transitions")
        
        feature_text = " with " + ", ".join(features) if features else ""
        complexity_text = "sophisticated" if is_complex else "professional"
        
        return f"I've designed a {complexity_text} landing page titled '{title}'{feature_text}. The design uses modern web standards with responsive breakpoints and follows accessibility best practices. The color scheme creates a strong brand presence while maintaining excellent readability."

    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML"""
        if not html_content:
            return "Generated Page"
        
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return title_match.group(1) if title_match else "Generated Page"

    def _determine_type(self, html_content: str, user_input: str) -> str:
        """Determine content type"""
        html_lower = html_content.lower()
        input_lower = user_input.lower()
        
        if "assessment" in html_lower or "assessment" in input_lower:
            return "assessment"
        elif "landing" in html_lower or "hero" in html_lower:
            return "landing-page"
        elif "portfolio" in html_lower:
            return "portfolio" 
        elif "dashboard" in html_lower:
            return "dashboard"
        else:
            return "custom"

    def _get_fallback_response(self, user_input: str, error_message: str) -> DualResponse:
        """Create fallback response when generation fails"""
        fallback_html = self._create_fallback_html(user_input)
        conversation = f"{error_message} I've created a placeholder design based on your request."
        
        metadata = {
            "title": "Fallback Page",
            "type": "fallback",
            "is_fallback": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": 1
        }
        
        return DualResponse(
            html_output=fallback_html,
            conversation=conversation,
            metadata=metadata
        )

    def _create_fallback_html(self, user_request: str) -> str:
        """Create professional fallback HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI HTML Builder - Processing Request</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 2rem; color: #152835; line-height: 1.6;
        }}
        .container {{
            max-width: 700px; background: white; border-radius: 16px; padding: 3rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); text-align: center;
        }}
        .header {{
            background: linear-gradient(135deg, #003366 0%, #0066CF 100%);
            color: white; padding: 2.5rem; border-radius: 12px; margin-bottom: 2rem;
        }}
        .header h1 {{ font-size: 2.5rem; font-weight: 600; margin-bottom: 0.5rem; }}
        .header p {{ font-size: 1.2rem; opacity: 0.9; }}
        .request-box {{
            background: linear-gradient(135deg, #e6f3ff 0%, #f0f8ff 100%);
            border: 2px solid #66A9E2; border-radius: 12px;
            padding: 2rem; margin: 2rem 0;
        }}
        .request-box h3 {{ color: #003366; margin-bottom: 1rem; font-size: 1.3rem; }}
        .request-content {{ 
            background: white; padding: 1.5rem; border-radius: 8px;
            font-family: 'Courier New', monospace; color: #152835;
            border-left: 4px solid #0066CF; text-align: left;
        }}
        .status {{ margin: 1.5rem 0; color: #666; font-size: 1.1rem; }}
        .features {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem; margin: 2rem 0;
        }}
        .feature {{
            background: #f8f9fa; padding: 1rem; border-radius: 8px;
            border-left: 3px solid #0066CF;
        }}
        .retry-button {{
            background: linear-gradient(135deg, #0066CF 0%, #003366 100%);
            color: white; padding: 1rem 2.5rem; border: none; border-radius: 8px;
            font-size: 1.1rem; font-weight: 600; cursor: pointer; 
            transition: all 0.3s ease; margin-top: 1.5rem;
        }}
        .retry-button:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(0, 102, 207, 0.3); 
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AI HTML Builder</h1>
            <p>Revolutionary Claude-Powered Design Assistant</p>
        </div>
        
        <div class="request-box">
            <h3>📝 Your Creative Request</h3>
            <div class="request-content">{user_request}</div>
        </div>
        
        <div class="status">
            ⚡ Powered by Claude Sonnet 4 for superior design quality
        </div>
        
        <div class="features">
            <div class="feature">
                <strong>🎨 Professional Design</strong><br>
                Modern layouts with brand consistency
            </div>
            <div class="feature">
                <strong>📱 Responsive</strong><br>
                Perfect on all devices
            </div>
            <div class="feature">
                <strong>♿ Accessible</strong><br>
                WCAG AA compliant
            </div>
        </div>
        
        <p>I'm creating something exceptional for you with advanced design capabilities. This placeholder demonstrates our professional styling approach.</p>
        
        <button class="retry-button" onclick="location.reload()">
            ✨ Generate My Design
        </button>
    </div>
</body>
</html>"""


# Global Claude service instance
claude_service = ClaudeService()