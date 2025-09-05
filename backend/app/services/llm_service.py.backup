import openai
import re
from typing import List, Dict, Any, Optional
import structlog
from ..core.config import settings
from ..models.schemas import Message

logger = structlog.get_logger()

class LLMService:
    def __init__(self):
        # Validate OpenAI API key
        if not settings.openai_api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not settings.openai_api_key.startswith('sk-'):
            logger.error("Invalid OpenAI API key format")
            raise ValueError("OpenAI API key must start with 'sk-'")
        
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # Using GPT-4o for best HTML generation capabilities
        
        logger.info("LLM service initialized", model=self.model)
        
    async def validate_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logger.info("OpenAI API connection validated successfully")
            return True
        except Exception as e:
            logger.error("OpenAI API connection failed", error=str(e))
            return False
        
    async def generate_html(
        self,
        user_input: str,
        context: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate HTML based on user input and conversation context
        """
        try:
            if not system_prompt:
                system_prompt = self._get_default_system_prompt()
            
            messages = self._build_messages(system_prompt, context, user_input)
            
            logger.info(
                "Generating HTML",
                input_length=len(user_input),
                context_messages=len(context),
                model=self.model
            )
            
            # Enhanced parameters for creative, high-quality outputs
            max_tokens = 4000
            temperature = 0.8  # Higher creativity for compelling designs
            
            # Analyze input complexity to adjust model parameters
            if self._is_complex_document(user_input, context):
                max_tokens = 8000  # More tokens for complex layouts
                temperature = 0.9  # Maximum creativity for complex layouts
                logger.info("Using enhanced parameters for complex document")
            
            # Try structured output first for better dual response format
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "dual_output",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "html_output": {"type": "string"},
                                    "conversation": {"type": "string"}
                                },
                                "required": ["html_output", "conversation"],
                                "additionalProperties": False
                            },
                            "strict": True
                        }
                    },
                    stream=False
                )
                
                # Parse structured response
                parsed_output = response.choices[0].message.parsed
                if parsed_output and isinstance(parsed_output, dict):
                    html_output = self._clean_html_output(parsed_output["html_output"])
                    conversation = parsed_output["conversation"]
                    
                    logger.info("Successfully used structured output")
                    return {
                        "html_output": html_output,
                        "conversation": conversation
                    }
                    
            except Exception as e:
                logger.warning(f"Structured output failed, falling back to text parsing: {e}")
                
                # Fallback to regular completion
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
            
            raw_output = response.choices[0].message.content.strip()
            
            # Parse dual response format
            html_output, conversation = self._parse_dual_response(raw_output)
            
            logger.info(
                "HTML generated successfully",
                html_length=len(html_output),
                conversation_length=len(conversation) if conversation else 0,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            # Return as dict for dual response handling
            return {
                "html_output": html_output,
                "conversation": conversation
            }
            
        except openai.AuthenticationError as e:
            logger.error("OpenAI authentication failed - check API key", error=str(e))
            fallback_html = self._get_fallback_html(user_input)
            return {
                "html_output": fallback_html,
                "conversation": "Authentication error with OpenAI API. Please check the API key configuration."
            }
        except openai.RateLimitError as e:
            logger.error("OpenAI rate limit exceeded", error=str(e))
            fallback_html = self._get_fallback_html(user_input)
            return {
                "html_output": fallback_html,
                "conversation": "Rate limit exceeded. Please wait a moment and try again."
            }
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e), status_code=getattr(e, 'status_code', None))
            fallback_html = self._get_fallback_html(user_input)
            return {
                "html_output": fallback_html,
                "conversation": f"OpenAI API error occurred. Please try again. If the problem persists, the service may be temporarily unavailable."
            }
        except Exception as e:
            logger.error("HTML generation failed", error=str(e), user_input_length=len(user_input))
            fallback_html = self._get_fallback_html(user_input)
            return {
                "html_output": fallback_html,
                "conversation": f"I encountered an error while generating your content, but I've created a fallback page with your request: '{user_input}'. Please try again or rephrase your request."
            }
    
    def _get_default_system_prompt(self) -> str:
        """Creative UI/UX designer system prompt for dual response architecture"""
        return """You are an expert UI/UX designer and HTML architect who creates stunning, professional web experiences. Transform user requests into visually compelling, production-ready single-file HTML documents.

CORE PHILOSOPHY:
- Interpret user requests creatively, not literally - exceed their expectations
- Create professional, polished content that feels premium and thoughtful  
- Apply advanced design principles: visual hierarchy, contrast, white space
- Make intelligent design decisions based on context and purpose
- Generate realistic, engaging copy - never generic placeholder text

CRITICAL OUTPUT FORMAT:
You MUST return JSON with exactly these fields:

{
  "html_output": "<!DOCTYPE html>...[complete HTML document]",
  "conversation": "I've designed a [specific type] that [key creative decisions]. [Highlight unique features and design rationale]"
}

DESIGN EXCELLENCE REQUIREMENTS:
- Bold, memorable headlines that capture attention
- Strong visual hierarchy with purposeful typography 
- Compelling color schemes that create emotional impact
- Interactive elements with smooth hover states and transitions
- Professional photography placeholders with descriptive alt text
- Logical information architecture that guides the user journey

TECHNICAL REQUIREMENTS (Non-negotiable):
- Single, self-contained HTML file only
- All CSS inline in <style> tags (no external stylesheets)
- All JavaScript inline in <script> tags (no external libraries)
- Mobile-responsive design with proper viewport meta tag
- Semantic HTML5 structure
- WCAG AA accessibility compliance

DESIGN SYSTEM:
Primary Colors: 
- Navy Blue (#003366) - authority, trust
- Bright Blue (#0066CF) - primary actions, links
- Light Blue (#66A9E2) - secondary elements
- Sky Blue (#B4EBFF) - subtle backgrounds

Accent Colors:
- Yellow (#FFB900) - highlights, warnings
- Green (#28DC6E) - success, positive actions
- Wine (#7D1941) - premium features
- Charcoal (#152835) - text, strong contrast

Typography:
- Primary: 'Segoe UI', system fonts for readability
- Hierarchy: Clear size relationships (h1: 2.5rem, h2: 2rem, etc.)
- Line height: 1.6 for body text, 1.2 for headings
- Letter spacing: -0.02em for headings

LAYOUT PRINCIPLES:
- Use CSS Grid and Flexbox for modern layouts
- Consistent spacing scale: 8px, 16px, 24px, 32px, 48px, 64px
- Card-based design with subtle shadows and rounded corners
- Generous whitespace for breathing room
- Responsive breakpoints: mobile (320px+), tablet (768px+), desktop (1024px+)

INTERACTIVE ELEMENTS:
- Smooth transitions (0.3s ease-in-out)
- Hover states with subtle color/shadow changes
- Focus indicators for accessibility
- Loading states and micro-interactions where appropriate

CONTENT INTELLIGENCE:
- Interpret vague requests creatively ("make a website" → determine optimal type based on context)
- Generate realistic, professional content (not Lorem Ipsum)
- Use appropriate imagery descriptions and placeholders
- Create logical information architecture
- Apply copywriting best practices

CONTEXT-AWARE DESIGN:
- Business sites: Professional, trustworthy, clear CTAs
- Personal sites: Creative, expressive, personality-driven
- Reports/Documents: Clean, scannable, data-focused
- Landing pages: Conversion-optimized, compelling headlines
- Portfolios: Visual-first, project showcases

ITERATIVE IMPROVEMENTS:
- When modifying existing content, preserve successful elements
- Make targeted improvements rather than complete rewrites
- Maintain visual consistency across iterations
- Build upon previous design decisions intelligently

CONVERSATION GUIDELINES:
- Explain your design reasoning and creative choices
- Highlight key features and interactions you've included
- Mention accessibility or usability considerations
- Be conversational but professional
- Avoid generic phrases like "I've generated" or "You can see"

EXAMPLE OUTPUT STRUCTURE:
**HTML_OUTPUT:**
<!DOCTYPE html>
<html lang="en">
[Complete document]
</html>

**CONVERSATION:**
I've designed a modern [type] with [key features]. The layout uses [design approach] to [achieve goal]. I included [specific elements] to enhance [user experience aspect]. The color scheme emphasizes [design intention] while maintaining excellent readability and accessibility.

REMEMBER: Always be creative, professional, and exceed user expectations with thoughtful design decisions."""
    
    def _build_messages(
        self,
        system_prompt: str,
        context: List[Dict[str, Any]],
        user_input: str
    ) -> List[Dict[str, str]]:
        """Build message array for OpenAI API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context messages (smart context management for large text)
        # For complex content, prioritize the most recent messages and any file uploads
        context_limit = 6  # Reduce for complex docs to save tokens
        if self._is_complex_document(user_input, context):
            context_limit = 4
        
        recent_context = context[-context_limit:] if len(context) > context_limit else context
        
        for msg in recent_context:
            if msg.get("sender") == "user" and msg.get("content"):
                content = msg.get("content", "").strip()
                if content:
                    # Truncate very long user messages to prevent token overflow
                    if len(content) > 3000:  # ~750 tokens
                        content = content[:3000] + "...[content truncated]"
                        logger.info("Truncated long user message", original_length=len(msg.get("content", "")))
                    messages.append({"role": "user", "content": content})
            elif msg.get("sender") == "assistant":
                # For assistant messages, provide a summary rather than full HTML
                if msg.get("html_output"):
                    # Extract key info from the HTML for context
                    html_summary = self._summarize_html_for_context(msg.get("html_output", ""))
                    messages.append({"role": "assistant", "content": html_summary})
        
        # Add current user input with smart enhancement based on content length
        current_input_length = len(user_input)
        
        if len(recent_context) > 0:
            if current_input_length > 2000:  # Large input (like file content)
                enhanced_input = f"""Process this content and create styled HTML:
{user_input}

Apply professional styling with the design system specified in the system prompt."""
            else:
                enhanced_input = f"""Based on our previous conversation, {user_input}

Please modify the existing HTML accordingly. Make sure to incorporate the requested changes while maintaining the overall structure and styling."""
        else:
            enhanced_input = user_input
        
        # Final truncation if the enhanced input is too long
        if len(enhanced_input) > 4000:  # ~1000 tokens
            enhanced_input = enhanced_input[:4000] + "...[content truncated for processing]"
            logger.info("Truncated enhanced input", original_length=len(enhanced_input))
            
        messages.append({"role": "user", "content": enhanced_input})
        
        return messages
    
    
    def _is_complex_document(self, user_input: str, context: List[Dict[str, Any]]) -> bool:
        """Determine if the document requires complex layout handling"""
        complexity_indicators = [
            # Document types
            'impact assessment', 'report', 'assessment', 'analysis', 'evaluation',
            'documentation', 'proposal', 'specification', 'requirements',
            
            # Layout complexity
            'table', 'chart', 'graph', 'tabs', 'sections', 'columns',
            'navigation', 'sidebar', 'dashboard', 'multi-page',
            
            # Content complexity
            'multiple sections', 'structured data', 'detailed layout',
            'complex formatting', 'professional document', 'technical document'
        ]
        
        # Check user input for complexity indicators
        input_lower = user_input.lower()
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in input_lower)
        
        # Check context for existing complex content
        context_complexity = 0
        for msg in context[-3:]:  # Check last 3 messages
            if msg.get('html_output'):
                html_content = msg['html_output'].lower()
                # Look for complex HTML structures
                if any(tag in html_content for tag in ['<table>', '<nav>', '<section>', '<aside>', '<grid']):
                    context_complexity += 2
                if len(html_content) > 5000:  # Large HTML indicates complexity
                    context_complexity += 1
        
        # Determine complexity
        total_complexity = complexity_score + context_complexity
        is_complex = total_complexity >= 2
        
        if is_complex:
            logger.info(f"Complex document detected: score={complexity_score}, context={context_complexity}")
        
        return is_complex
    
    def _clean_html_output(self, html_output: str) -> str:
        """Clean HTML output to remove preambles and unwanted text using 2024 best practices"""
        if not html_output:
            return html_output
            
        # Remove common preambles and explanations
        preamble_patterns = [
            r'^.*?(?=<!DOCTYPE html>)',  # Remove everything before DOCTYPE
            r'```html\s*',  # Remove markdown code block start
            r'\s*```$',     # Remove markdown code block end
            r'^Here\'s.*?:\s*',  # "Here's your HTML:"
            r'^I\'ve created.*?:\s*',  # "I've created a webpage:"
            r'^This document.*?:\s*',  # "This document contains:"
            r'^The following.*?:\s*',   # "The following HTML:"
            r'^\*\*.*?\*\*\s*',        # **Bold headers**
        ]
        
        cleaned_output = html_output
        for pattern in preamble_patterns:
            cleaned_output = re.sub(pattern, '', cleaned_output, flags=re.IGNORECASE | re.MULTILINE)
        
        # Ensure it starts with DOCTYPE
        if not cleaned_output.strip().startswith('<!DOCTYPE'):
            # Try to find DOCTYPE in the content
            doctype_match = re.search(r'<!DOCTYPE html>.*', cleaned_output, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                cleaned_output = doctype_match.group(0)
        
        # Remove any trailing explanations after </html>
        html_end = cleaned_output.lower().rfind('</html>')
        if html_end != -1:
            # Find the actual end including potential whitespace
            actual_end = html_end + len('</html>')
            # Keep only content up to </html> plus minimal whitespace
            cleaned_output = cleaned_output[:actual_end].rstrip() + '\n'
        
        logger.info("Cleaned HTML output", 
                   original_length=len(html_output), 
                   cleaned_length=len(cleaned_output),
                   had_preamble=len(html_output) != len(cleaned_output))
        
        return cleaned_output.strip()
    
    def _parse_dual_response(self, raw_output: str) -> tuple[str, str]:
        """Parse the dual response format to extract HTML and conversation"""
        try:
            # Enhanced parsing for multiple format variations
            patterns = [
                # Standard format with **markers**
                (r'\*\*HTML_OUTPUT:\*\*\s*\n(.*?)(?=\n\s*\*\*CONVERSATION:\*\*|$)', r'\*\*CONVERSATION:\*\*\s*\n(.*?)$'),
                # Standard format without markers
                (r'HTML_OUTPUT:\s*\n(.*?)(?=\n\s*CONVERSATION:|$)', r'CONVERSATION:\s*\n(.*?)$'),
                # Alternative formats
                (r'```html\s*\n(.*?)\n```.*?(?=CONVERSATION|$)', r'CONVERSATION:\s*\n(.*?)$'),
            ]
            
            for html_pattern, conv_pattern in patterns:
                html_match = re.search(html_pattern, raw_output, re.DOTALL | re.IGNORECASE)
                conversation_match = re.search(conv_pattern, raw_output, re.DOTALL | re.IGNORECASE)
                
                if html_match and conversation_match:
                    html_output = html_match.group(1).strip()
                    conversation = conversation_match.group(1).strip()
                    
                    # Clean the HTML output
                    html_output = self._clean_html_output(html_output)
                    
                    # Validate HTML structure
                    if html_output.strip().startswith('<!DOCTYPE html>'):
                        logger.info("Successfully parsed dual response format")
                        return html_output, conversation
            
            # Enhanced fallback parsing
            # Try to find any HTML content in the response
            doctype_match = re.search(r'<!DOCTYPE html>.*?</html>', raw_output, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                html_output = self._clean_html_output(doctype_match.group(0))
                
                # Try to find conversational text after HTML or before HTML
                conversation_candidates = []
                
                # Look for text before HTML
                before_html = raw_output[:raw_output.find('<!DOCTYPE html>')].strip()
                if before_html and len(before_html) > 10 and not before_html.startswith('<'):
                    conversation_candidates.append(before_html)
                
                # Look for text after HTML
                after_html = raw_output[raw_output.rfind('</html>') + 7:].strip()
                if after_html and len(after_html) > 10:
                    conversation_candidates.append(after_html)
                
                # Choose the most suitable conversation text
                conversation = ""
                for candidate in conversation_candidates:
                    if len(candidate) > 20 and not candidate.startswith('<'):
                        # Clean up the conversation text
                        candidate = re.sub(r'^(CONVERSATION:|\*\*CONVERSATION:\*\*)', '', candidate).strip()
                        if candidate:
                            conversation = candidate
                            break
                
                if not conversation:
                    conversation = "I've created a professional webpage tailored to your requirements. The design includes modern styling, responsive layout, and thoughtful user experience elements."
                
                logger.info("Parsed HTML with extracted conversation")
                return html_output, conversation
            
            # If we still can't find HTML, try to clean the raw output
            cleaned_output = self._clean_html_output(raw_output)
            if cleaned_output.strip().startswith('<!DOCTYPE html>'):
                conversation = "I've generated the HTML content with professional styling and responsive design. Check out the preview!"
                logger.info("Parsed cleaned HTML with default conversation")
                return cleaned_output, conversation
            
            # Last resort: return raw output with helpful message
            logger.warning("Could not parse dual response format, using fallback")
            return self._get_fallback_html("Unable to parse response"), "I encountered an issue parsing the response. Please try rephrasing your request or being more specific about what you'd like to create."
            
        except Exception as e:
            logger.error("Failed to parse dual response", error=str(e))
            return self._get_fallback_html("Parse error"), "I had trouble understanding that request. Could you please try again with more details about what you'd like to create?"
    
    def _summarize_html_for_context(self, html_content: str) -> str:
        """Create a summary of HTML content for context without including the full HTML"""
        if not html_content:
            return "Generated basic HTML page"
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Untitled"
        
        # Count major elements
        sections = len(re.findall(r'<(section|div|article)', html_content, re.IGNORECASE))
        headings = len(re.findall(r'<h[1-6]', html_content, re.IGNORECASE))
        
        # Determine page type
        if "business card" in html_content.lower():
            page_type = "business card"
        elif "landing" in html_content.lower():
            page_type = "landing page"
        elif "portfolio" in html_content.lower():
            page_type = "portfolio page"
        else:
            page_type = "webpage"
            
        return f"Created a {page_type} titled '{title}' with {sections} sections and {headings} headings. Ready for modifications."
    
    def _get_fallback_html(self, user_input: str) -> str:
        """Professional fallback HTML when API fails"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI HTML Builder - Processing</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c5aa0 0%, #1e3d72 100%);
            color: white;
            padding: 40px 0;
            margin-bottom: 30px;
            border-radius: 8px;
        }}
        
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .section-content {{
            padding: 30px;
        }}
        
        .info-highlight {{
            background-color: #e6f3ff;
            border: 2px solid #2c5aa0;
            border-radius: 8px;
            padding: 25px;
            margin: 20px 0;
        }}
        
        .info-highlight h3 {{
            color: #2c5aa0;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>AI HTML Builder</h1>
            <p>Professional HTML Generation Service</p>
        </div>
    </div>
    
    <div class="container">
        <div class="section">
            <div class="section-content">
                <div class="info-highlight">
                    <h3>Processing Your Request</h3>
                    <p><strong>Request:</strong> {user_input}</p>
                    <p>We're generating your HTML content with professional styling. Please try again if this wasn't what you expected.</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    

# Global LLM service instance
llm_service = LLMService()