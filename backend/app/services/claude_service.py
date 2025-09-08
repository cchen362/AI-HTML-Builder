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
        session_id: str
    ) -> DualResponse:
        """
        Generate high-quality HTML and conversation using Claude Sonnet 4
        """
        logger.info("[DEBUG] Claude generate_dual_response method called!", session_id=session_id, user_input_length=len(user_input))
        try:
            # Build simple message structure
            system_prompt, messages = self._build_simple_messages(user_input, context)
            
            # Enhanced parameters for iterative editing and larger outputs
            max_tokens = 8000  # Increased for larger HTML documents and context
            temperature = 0.7
            
            logger.info(
                "[CLAUDE API CALL] Generating with Claude Sonnet 4",
                model=self.model,
                input_length=len(user_input),
                context_messages=len(context),
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Call Claude API with retry logic
            response = self._call_claude_with_retry(system_prompt, messages, max_tokens, temperature)
            
            logger.info(
                "[CLAUDE API RESPONSE] Received response from Claude",
                response_length=len(response.content[0].text),
                usage_tokens=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
            )
            
            # Simple response parsing - expect pure HTML
            html_output = self._parse_simple_response(response.content[0].text)
            conversation = self._generate_simple_conversation(html_output, user_input)
            
            # Generate metadata
            metadata = {
                "model": self.model,
                "title": self._extract_title(html_output),
                "type": self._determine_type(html_output, user_input),
                "timestamp": datetime.utcnow().isoformat(),
                "version": 1,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
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

    def _get_surgical_system_prompt(self) -> str:
        """
        System prompt optimized for surgical HTML editing
        """
        return """You are an expert HTML/CSS designer specializing in precise, targeted modifications to existing HTML documents.

SURGICAL EDITING APPROACH:
- When modifying existing HTML, make ONLY the specific changes requested
- Preserve all existing styling, structure, and functionality not explicitly mentioned
- Keep the same CSS classes, IDs, and JavaScript interactions intact
- Maintain responsive design and brand consistency

MODIFICATION GUIDELINES:
1. Identify the exact section/element to modify (e.g., header title, specific div, particular section)
2. Change only that targeted element while preserving everything else
3. Keep all existing CSS styling unless specifically asked to change styling
4. Maintain the same HTML structure and class names
5. Preserve all interactive elements (tabs, buttons, JavaScript)

BRAND CONSISTENCY:
- Use existing blue colors (#003366, #0066CF) already in the document
- Match existing typography and spacing
- Keep the same design patterns and layout structure

OUTPUT REQUIREMENTS:
- Return ONLY the complete modified HTML document
- No explanations or additional text
- Ensure seamless integration with existing design
- Maintain professional quality and accessibility"""

    def _get_simple_system_prompt(self) -> str:
        """
        Enhanced system prompt that supports both new creation and iterative editing
        """
        return """You are an expert HTML/CSS designer who creates and modifies professional single-file HTML documents.

For NEW requests: Create a complete, production-ready HTML file with:
- All CSS inline in <style> tags
- All JavaScript inline in <script> tags (if needed)  
- Mobile-responsive design
- Professional appearance using blue (#003366, #0066CF), white, and grey brand colors
- Clean, minimal UI elements
- Modern design principles

For MODIFICATION requests: Update the existing HTML while preserving:
- Overall structure and design consistency
- Brand colors and styling approach
- Responsive behavior
- All inline CSS/JS approach
- Any interactive elements (tabs, buttons, etc.)

IMPORTANT: 
- Always return ONLY the complete HTML document starting with <!DOCTYPE html>
- No explanations, markdown formatting, or additional text
- Ensure all modifications integrate seamlessly with existing design
- Maintain professional quality throughout"""

    def _build_simple_messages(self, user_input: str, context: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, str]]]:
        """Build message structure optimized for surgical editing and prompt caching"""
        
        # Detect if this is a modification request
        modification_words = ["change", "modify", "update", "adjust", "fix", "edit", "improve", "enhance", "make", "add", "remove", "alter", "delete"]
        is_modification = any(word in user_input.lower() for word in modification_words)
        
        # Use surgical editing prompt for modifications
        if is_modification and context and len(context) > 0:
            system_prompt = self._get_surgical_system_prompt()
            messages = self._build_surgical_edit_messages(user_input, context)
            logger.info("[CLAUDE MESSAGES] Using surgical editing approach", 
                       message_count=len(messages), 
                       modification_detected=True)
        else:
            system_prompt = self._get_simple_system_prompt()
            messages = self._build_creation_messages(user_input, context)
            logger.info("[CLAUDE MESSAGES] Using creation approach", 
                       message_count=len(messages), 
                       modification_detected=False)
        
        return system_prompt, messages

    def _build_surgical_edit_messages(self, user_input: str, context: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Build messages specifically for surgical editing with prompt caching"""
        messages = []
        
        # Find the current HTML document
        last_html = None
        for msg in reversed(context):
            if msg.get("sender") == "assistant" and msg.get("html_output"):
                last_html = msg["html_output"]
                break
        
        if last_html:
            # Add HTML context with caching for efficiency
            html_content = self._prepare_html_for_context(last_html)
            
            # Use prompt caching for the HTML document (it's likely to be reused)
            cache_control_message = {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": f"Current HTML document to modify:\n\n```html\n{html_content}\n```",
                        "cache_control": {"type": "ephemeral"}  # Cache this HTML content
                    }
                ]
            }
            messages.append(cache_control_message)
            
            # Add instruction for surgical editing
            messages.append({
                "role": "assistant", 
                "content": "I can see the current HTML document. I'll make precise modifications while preserving all existing styling and structure."
            })
        
        # Add the specific modification request
        messages.append({"role": "user", "content": user_input})
        
        return messages

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
        """Simple parsing - expect pure HTML response"""
        try:
            response_text = response_text.strip()
            
            # If it starts with DOCTYPE, use it directly
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
        """Prepare HTML content for context, managing token limits intelligently"""
        if not html_content:
            return "No HTML content available."
        
        try:
            # Token limit for HTML context (roughly 4000 tokens = ~16000 characters)
            MAX_HTML_CONTEXT_LENGTH = 15000
            
            if len(html_content) <= MAX_HTML_CONTEXT_LENGTH:
                # Small enough to include in full
                return html_content
            
            # For larger HTML, include critical sections
            html_lower = html_content.lower()
            
            # Extract critical sections
            sections = []
            
            # 1. Always include DOCTYPE and opening tags
            doctype_match = re.search(r'(<!DOCTYPE.*?<head>.*?</head>)', html_content, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                sections.append(doctype_match.group(1))
            
            # 2. Include body opening and main structure
            body_start_match = re.search(r'<body[^>]*>', html_content, re.IGNORECASE)
            if body_start_match:
                body_start = body_start_match.end()
                
                # Find main content containers
                main_containers = []
                container_patterns = [
                    r'<div class="container[^"]*"[^>]*>.*?</div>',
                    r'<main[^>]*>.*?</main>',
                    r'<section[^>]*>.*?</section>',
                    r'<header[^>]*>.*?</header>'
                ]
                
                for pattern in container_patterns:
                    matches = re.finditer(pattern, html_content[body_start:], re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        container_content = match.group(0)
                        # Truncate individual containers if too long
                        if len(container_content) > 3000:
                            container_content = container_content[:3000] + "... [truncated]"
                        main_containers.append(container_content)
                        
                        # Stop if we have enough content
                        if sum(len(s) for s in sections + main_containers) > MAX_HTML_CONTEXT_LENGTH:
                            break
                    
                    if sum(len(s) for s in sections + main_containers) > MAX_HTML_CONTEXT_LENGTH:
                        break
                
                sections.extend(main_containers)
            
            # 3. Always include closing body and html tags
            sections.append("</body>\n</html>")
            
            # Combine sections
            context_html = '\n'.join(sections)
            
            # Final truncation if still too long
            if len(context_html) > MAX_HTML_CONTEXT_LENGTH:
                context_html = context_html[:MAX_HTML_CONTEXT_LENGTH] + "\n... [HTML truncated for context]"
            
            logger.info("Prepared HTML context for modification", 
                       original_length=len(html_content), 
                       context_length=len(context_html))
            
            return context_html
        
        except Exception as e:
            logger.warning("Failed to prepare HTML context", error=str(e))
            # Fallback to simple truncation
            if len(html_content) > 15000:
                return html_content[:15000] + "\n... [HTML truncated]"
            return html_content

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