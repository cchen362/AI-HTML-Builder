"""
Revolutionary Conversational LLM Service

This service acts as a conversational UI/UX designer that generates both
HTML artifacts AND natural conversation responses, creating a Claude Artifacts-style
experience with clean separation between dialogue and rendered content.
"""

import openai
import re
import json
from typing import List, Dict, Any, Optional, NamedTuple
from datetime import datetime
import structlog
from ..core.config import settings
from ..models.schemas import Message

logger = structlog.get_logger()

class DualResponse(NamedTuple):
    """Structured dual response containing both HTML artifact and conversation"""
    html_output: str
    conversation: str
    metadata: Dict[str, Any]

class ConversationContext(NamedTuple):
    """Context information for generating intelligent responses"""
    messages: List[Dict[str, Any]]
    session_id: str
    iteration_count: int
    current_html: Optional[str] = None

class Intent(NamedTuple):
    """User intent analysis results"""
    type: str  # 'create_new', 'modify_existing', 'style_change', 'content_addition'
    complexity: str  # 'simple', 'medium', 'complex'
    is_large_content: bool
    keywords: List[str]

class ConversationalLLMService:
    """
    Revolutionary LLM service that acts as a conversational UI/UX designer.
    Generates both HTML artifacts AND natural conversation responses for
    a Claude Artifacts-style experience.
    """
    
    def __init__(self):
        # Validate OpenAI API key
        if not settings.openai_api_key:
            logger.error("OpenAI API key not configured")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not settings.openai_api_key.startswith('sk-'):
            logger.error("Invalid OpenAI API key format")
            raise ValueError("OpenAI API key must start with 'sk-'")
        
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # Latest model for best creativity and intelligence
        
        logger.info("Conversational LLM service initialized", model=self.model)
        
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

    async def generate_dual_response(
        self, 
        user_input: str, 
        context: ConversationContext
    ) -> DualResponse:
        """
        Generate both HTML artifact and conversational response
        This is the core method that creates the Claude Artifacts-style experience
        """
        try:
            # Analyze user intent and complexity
            intent = self._analyze_intent(user_input, context)
            logger.info("Intent analyzed", intent_type=intent.type, complexity=intent.complexity)
            
            # Build conversation messages with creative system prompt
            messages = self._build_conversation_messages(user_input, context, intent)
            
            # Determine model parameters based on complexity
            model_params = self._get_model_parameters(intent)
            
            logger.info(
                "Generating dual response",
                input_length=len(user_input),
                context_messages=len(context.messages),
                intent_type=intent.type,
                complexity=intent.complexity,
                is_large_content=intent.is_large_content
            )
            
            # Generate response with enhanced parameters
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **model_params
            )
            
            raw_output = response.choices[0].message.content.strip()
            
            # Parse the dual response format
            html_output, conversation = self._parse_dual_response_format(raw_output)
            
            # Generate metadata
            metadata = self._generate_metadata(html_output, conversation, intent)
            
            logger.info(
                "Dual response generated successfully",
                html_length=len(html_output),
                conversation_length=len(conversation),
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return DualResponse(
                html_output=html_output,
                conversation=conversation,
                metadata=metadata
            )
            
        except openai.AuthenticationError as e:
            logger.error("OpenAI authentication failed", error=str(e))
            return self._get_fallback_response(user_input, "Authentication error with OpenAI API. Please check the API key configuration.")
            
        except openai.RateLimitError as e:
            logger.error("OpenAI rate limit exceeded", error=str(e))
            return self._get_fallback_response(user_input, "I'm experiencing high demand right now. Please wait a moment and try again.")
            
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e))
            return self._get_fallback_response(user_input, "I encountered a temporary issue with my creative engines. Please try again in a moment.")
            
        except Exception as e:
            logger.error("Dual response generation failed", error=str(e), user_input_length=len(user_input))
            return self._get_fallback_response(user_input, f"I encountered an unexpected issue while working on your request. Let me create a placeholder for now - please try again!")

    def _analyze_intent(self, user_input: str, context: ConversationContext) -> Intent:
        """Analyze user input to determine intent and provide appropriate response strategy"""
        input_lower = user_input.lower()
        
        # Determine intent type
        intent_type = "create_new"  # Default
        if context.current_html and any(keyword in input_lower for keyword in 
            ['change', 'update', 'modify', 'adjust', 'fix', 'alter', 'improve']):
            intent_type = "modify_existing"
        elif any(keyword in input_lower for keyword in 
            ['color', 'font', 'style', 'design', 'layout', 'look', 'appearance']):
            intent_type = "style_change"
        elif any(keyword in input_lower for keyword in 
            ['add', 'include', 'insert', 'append', 'put']):
            intent_type = "content_addition"
        
        # Determine complexity
        complexity_indicators = [
            'impact assessment', 'report', 'dashboard', 'documentation',
            'navigation', 'responsive', 'interactive', 'animation', 'form',
            'table', 'chart', 'sections', 'tabs', 'multi', 'complex'
        ]
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in input_lower)
        
        if complexity_score >= 3:
            complexity = "complex"
        elif complexity_score >= 1:
            complexity = "medium"
        else:
            complexity = "simple"
        
        # Check for large content
        is_large_content = len(user_input) > 500
        
        # Extract keywords
        keywords = [word for word in complexity_indicators if word in input_lower]
        
        return Intent(
            type=intent_type,
            complexity=complexity,
            is_large_content=is_large_content,
            keywords=keywords
        )

    def _get_creative_system_prompt(self) -> str:
        """Revolutionary creative system prompt for conversational AI designer"""
        return """You are an exceptional UI/UX designer and HTML architect with world-class creative taste and conversational skills. You create stunning, professional single-file HTML experiences while having natural conversations about your design decisions.

DUAL OUTPUT ARCHITECTURE:
You MUST always provide exactly two outputs in this format:

**HTML_ARTIFACT:**
[Complete production-ready HTML document with inline CSS and JavaScript - no explanations, just pure HTML starting with <!DOCTYPE html>]

**CONVERSATION:**
[Natural, friendly explanation of what you created, your design decisions, and helpful suggestions for next steps]

CREATIVE PHILOSOPHY:
- Interpret requests creatively and exceed expectations
- Create visually compelling, modern designs that feel premium and professional
- Use advanced CSS techniques: Grid, Flexbox, animations, gradients, shadows
- Apply exceptional typography, spacing, and visual hierarchy
- Generate realistic, engaging content - never Lorem Ipsum
- Make intelligent design decisions based on context and user needs

BRAND DESIGN SYSTEM:
Primary Colors:
- Navy Blue (#003366) - Authority, trust, headers, primary text
- Bright Blue (#0066CF) - Primary actions, links, interactive elements
- Light Blue (#66A9E2) - Secondary elements, hover states, accents
- Sky Blue (#B4EBFF) - Subtle backgrounds, highlights, borders

Accent Colors:
- Green (#28DC6E) - Success states, positive actions, confirmations
- Yellow (#FFB900) - Warnings, highlights, attention-grabbing elements
- Wine (#7D1941) - Premium features, luxury touches, special elements
- Charcoal (#152835) - Primary text, strong contrast, headers

Typography System:
- Primary: 'Inter', 'Segoe UI', system fonts for modern, clean readability
- Headers: Bold weights (600-700) with proper hierarchy
  - h1: 3rem (48px) with -0.02em letter-spacing
  - h2: 2.25rem (36px) with -0.01em letter-spacing
  - h3: 1.875rem (30px) with normal spacing
  - h4: 1.5rem (24px) with normal spacing
- Body: 16px base size, 1.6 line-height for optimal readability
- Small text: 14px for captions, 12px for fine print

Layout Principles:
- Generous whitespace and breathing room for elegance
- Consistent spacing scale: 8px, 16px, 24px, 32px, 48px, 64px
- Card-based designs with subtle shadows and rounded corners
- Smooth transitions (0.3s ease-in-out) and micro-interactions
- Mobile-first responsive design with thoughtful breakpoints
- CSS Grid for complex layouts, Flexbox for component-level arrangement

CONVERSATIONAL GUIDELINES:
- Explain your creative decisions thoughtfully and specifically
- Suggest concrete improvements and interesting variations
- Ask clarifying questions when it would be helpful
- Reference specific design principles you applied
- Be encouraging, collaborative, and enthusiastic about design
- Avoid generic phrases - be specific about what you created
- Share insights about why certain design choices work well
- Offer next steps or related improvements they might consider

TECHNICAL REQUIREMENTS:
- Single HTML file with all CSS inline in <style> tags
- All JavaScript inline in <script> tags - no external dependencies
- Semantic HTML5 structure for accessibility and SEO
- WCAG AA accessibility compliance with proper contrast ratios
- Mobile-responsive design with viewport meta tag
- Clean, well-formatted code with logical structure

CONTENT CREATION:
- Generate realistic, professional content that fits the context
- Create compelling headlines and engaging copy
- Use appropriate placeholder images with descriptive alt text
- Structure information logically and scannable
- Apply copywriting best practices for clarity and engagement

EXAMPLE CONVERSATION STYLE:
"I've designed a modern impact assessment report with a striking gradient header that immediately establishes authority and professionalism. The layout uses CSS Grid to create a clean, scannable structure with your content organized into logical sections. I included interactive tabs for easy navigation and used card-based design with subtle shadows to create visual separation. The color scheme emphasizes trust and reliability with our navy blues, while the typography hierarchy guides readers through the information naturally. Would you like me to add more interactive elements, adjust the visual emphasis, or modify the content structure?"

ITERATION INTELLIGENCE:
When modifying existing content:
- Preserve successful elements and overall design coherence
- Make targeted improvements rather than complete rewrites
- Build upon previous design decisions intelligently
- Reference what you're changing and why
- Maintain visual consistency across iterations"""

    def _build_conversation_messages(
        self, 
        user_input: str, 
        context: ConversationContext, 
        intent: Intent
    ) -> List[Dict[str, str]]:
        """Build optimized message array for conversational AI generation"""
        messages = [{"role": "system", "content": self._get_creative_system_prompt()}]
        
        # Add contextual messages with smart management
        context_limit = 4 if intent.complexity == "complex" or intent.is_large_content else 6
        recent_context = context.messages[-context_limit:] if len(context.messages) > context_limit else context.messages
        
        for msg in recent_context:
            if msg.get("sender") == "user" and msg.get("content"):
                content = msg.get("content", "").strip()
                if content:
                    # Intelligent truncation for very long messages
                    if len(content) > 2000:
                        content = content[:2000] + "...[content continues - focusing on key points]"
                        logger.info("Truncated long context message", original_length=len(msg.get("content", "")))
                    messages.append({"role": "user", "content": content})
                    
            elif msg.get("sender") == "assistant":
                # Provide design context summary rather than full HTML
                if msg.get("html_output"):
                    summary = self._create_design_summary(msg.get("html_output", ""))
                    messages.append({"role": "assistant", "content": f"Previously created: {summary}"})
        
        # Enhanced current input based on intent and context
        enhanced_input = self._enhance_user_input(user_input, intent, context)
        
        # Final intelligent truncation if needed
        if len(enhanced_input) > 3000:
            enhanced_input = enhanced_input[:3000] + "...[focusing on key requirements]"
            logger.info("Truncated enhanced input", original_length=len(enhanced_input))
        
        messages.append({"role": "user", "content": enhanced_input})
        
        return messages

    def _enhance_user_input(self, user_input: str, intent: Intent, context: ConversationContext) -> str:
        """Enhance user input with context and intelligent processing"""
        if intent.is_large_content:
            return f"""I have detailed content to transform into HTML:

{user_input}

Please create a beautiful, professional HTML page that presents this content with excellent visual design, proper structure, and engaging layout. Apply the brand design system and make it look premium and polished."""
        
        if intent.type == "modify_existing" and context.current_html:
            return f"""Based on our current design, {user_input}

Please modify the existing HTML accordingly while maintaining the overall visual consistency and design quality. Make targeted improvements and explain what you're changing."""
        
        if intent.complexity == "complex":
            return f"""{user_input}

This appears to be a complex project - please create something sophisticated with advanced layout, interactive elements, and professional polish. Use your full creative capabilities."""
        
        return user_input

    def _get_model_parameters(self, intent: Intent) -> Dict[str, Any]:
        """Get optimized model parameters based on intent analysis"""
        base_params = {
            "temperature": 0.7,  # Balanced creativity and consistency
            "max_tokens": 4000,
            "stream": False
        }
        
        if intent.complexity == "complex" or intent.is_large_content:
            base_params["max_tokens"] = 6000
            base_params["temperature"] = 0.8  # More creativity for complex projects
        elif intent.type == "modify_existing":
            base_params["temperature"] = 0.6  # Slightly more focused for modifications
        
        return base_params

    def _parse_dual_response_format(self, raw_output: str) -> tuple[str, str]:
        """Parse the dual response format to extract HTML artifact and conversation"""
        try:
            # Enhanced parsing patterns for the dual format
            patterns = [
                # Standard format with **markers**
                (r'\*\*HTML_ARTIFACT:\*\*\s*\n(.*?)(?=\n\s*\*\*CONVERSATION:\*\*|$)', r'\*\*CONVERSATION:\*\*\s*\n(.*?)$'),
                # Alternative formats
                (r'HTML_ARTIFACT:\s*\n(.*?)(?=\n\s*CONVERSATION:|$)', r'CONVERSATION:\s*\n(.*?)$'),
                (r'```html\s*\n(.*?)\n```.*?(?=CONVERSATION|$)', r'CONVERSATION:\s*\n(.*?)$'),
            ]
            
            for html_pattern, conv_pattern in patterns:
                html_match = re.search(html_pattern, raw_output, re.DOTALL | re.IGNORECASE)
                conversation_match = re.search(conv_pattern, raw_output, re.DOTALL | re.IGNORECASE)
                
                if html_match and conversation_match:
                    html_output = self._clean_html_output(html_match.group(1).strip())
                    conversation = conversation_match.group(1).strip()
                    
                    if html_output.startswith('<!DOCTYPE html>'):
                        logger.info("Successfully parsed dual response format")
                        return html_output, conversation
            
            # Fallback: try to extract any HTML content
            doctype_match = re.search(r'<!DOCTYPE html>.*?</html>', raw_output, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                html_output = self._clean_html_output(doctype_match.group(0))
                
                # Extract conversation from remaining content
                conversation = self._extract_conversation_from_response(raw_output, html_output)
                
                logger.info("Parsed HTML with extracted conversation")
                return html_output, conversation
            
            # If no proper HTML found, create fallback
            logger.warning("Could not parse dual response format properly")
            fallback_html = self._create_fallback_html("Unable to parse response properly")
            fallback_conversation = "I had some difficulty parsing that request. Could you please try rephrasing what you'd like me to create?"
            
            return fallback_html, fallback_conversation
            
        except Exception as e:
            logger.error("Failed to parse dual response format", error=str(e))
            fallback_html = self._create_fallback_html("Parse error occurred")
            fallback_conversation = "I encountered a technical issue while processing your request. Please try again with more specific details about what you'd like to create."
            return fallback_html, fallback_conversation

    def _clean_html_output(self, html_output: str) -> str:
        """Clean HTML output removing preambles and explanations"""
        if not html_output:
            return html_output
        
        # Remove common preambles
        preamble_patterns = [
            r'^.*?(?=<!DOCTYPE html>)',  # Everything before DOCTYPE
            r'```html\s*',  # Markdown code blocks
            r'\s*```$',
            r'^Here\'s.*?:\s*',  # Explanatory text
            r'^I\'ve created.*?:\s*',
            r'^\*\*.*?\*\*\s*',  # Bold headers
        ]
        
        cleaned = html_output
        for pattern in preamble_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # Ensure starts with DOCTYPE
        if not cleaned.strip().startswith('<!DOCTYPE'):
            doctype_match = re.search(r'<!DOCTYPE html>.*', cleaned, re.DOTALL | re.IGNORECASE)
            if doctype_match:
                cleaned = doctype_match.group(0)
        
        # Remove trailing content after </html>
        html_end = cleaned.lower().rfind('</html>')
        if html_end != -1:
            cleaned = cleaned[:html_end + len('</html>')].rstrip() + '\n'
        
        return cleaned.strip()

    def _extract_conversation_from_response(self, raw_output: str, html_content: str) -> str:
        """Extract conversational content from the response"""
        # Remove the HTML content to find conversation
        without_html = raw_output.replace(html_content, '').strip()
        
        # Look for conversational text patterns
        conversation_candidates = []
        
        # Split by common separators and find meaningful content
        parts = re.split(r'\n\n+', without_html)
        for part in parts:
            part = part.strip()
            if (len(part) > 20 and 
                not part.startswith('<') and 
                not part.startswith('```') and
                not re.match(r'^\*\*(HTML_ARTIFACT|CONVERSATION):\*\*', part)):
                conversation_candidates.append(part)
        
        if conversation_candidates:
            # Choose the most substantial conversation piece
            best_conversation = max(conversation_candidates, key=len)
            return best_conversation
        
        # Default conversation if nothing found
        return "I've created a professional HTML page with modern design and responsive layout. The styling follows current best practices for visual hierarchy and user experience. Would you like me to make any adjustments to the design or content?"

    def _create_design_summary(self, html_content: str) -> str:
        """Create a brief summary of previous design for context"""
        if not html_content:
            return "basic HTML page"
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "webpage"
        
        # Count elements for context
        sections = len(re.findall(r'<(section|div|article)', html_content, re.IGNORECASE))
        
        # Determine type
        if "impact assessment" in html_content.lower():
            return f"impact assessment report '{title}' with {sections} sections"
        elif "landing" in html_content.lower():
            return f"landing page '{title}' with structured content"
        elif "portfolio" in html_content.lower():
            return f"portfolio page '{title}' with showcase sections"
        else:
            return f"webpage '{title}' with {sections} content sections"

    def _generate_metadata(self, html_output: str, conversation: str, intent: Intent) -> Dict[str, Any]:
        """Generate metadata about the created artifact"""
        return {
            "title": self._extract_title_from_html(html_output),
            "type": self._determine_content_type(html_output, intent),
            "complexity": intent.complexity,
            "word_count": len(html_output.split()),
            "has_interactions": "onclick" in html_output.lower() or "addEventListener" in html_output,
            "is_responsive": "@media" in html_output,
            "timestamp": datetime.utcnow().isoformat(),
            "version": 1  # Will be managed by artifact system
        }

    def _extract_title_from_html(self, html_content: str) -> str:
        """Extract title from HTML content"""
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return title_match.group(1) if title_match else "Generated Page"

    def _determine_content_type(self, html_content: str, intent: Intent) -> str:
        """Determine the type of content created"""
        html_lower = html_content.lower()
        
        if "impact assessment" in html_lower:
            return "impact-assessment"
        elif any(word in html_lower for word in ["landing", "hero", "cta"]):
            return "landing-page"
        elif "portfolio" in html_lower:
            return "portfolio"
        elif any(word in html_lower for word in ["article", "blog", "post"]):
            return "article"
        elif "dashboard" in html_lower:
            return "dashboard"
        else:
            return "custom"

    def _get_fallback_response(self, user_input: str, error_message: str) -> DualResponse:
        """Create a fallback response when main generation fails"""
        fallback_html = self._create_fallback_html(user_input)
        conversation = f"{error_message} I've created a placeholder design based on your request '{user_input}'. Please try again for a fully custom solution!"
        
        metadata = {
            "title": "Fallback Page",
            "type": "fallback",
            "complexity": "simple",
            "is_fallback": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": 1
        }
        
        return DualResponse(
            html_output=fallback_html,
            conversation=conversation,
            metadata=metadata
        )

    def _create_fallback_html(self, user_input: str) -> str:
        """Create professional fallback HTML when generation fails"""
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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            line-height: 1.6;
            color: #152835;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 600px;
            background: white;
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        .header {{
            background: linear-gradient(135deg, #003366 0%, #0066CF 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }}
        
        .header h1 {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}
        
        .content {{
            margin-bottom: 2rem;
        }}
        
        .request-box {{
            background: #e6f3ff;
            border: 2px solid #b4ebff;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1.5rem 0;
        }}
        
        .request-box h3 {{
            color: #003366;
            margin-bottom: 0.75rem;
        }}
        
        .request-content {{
            background: white;
            padding: 1rem;
            border-radius: 6px;
            font-family: monospace;
            color: #152835;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .retry-button {{
            background: linear-gradient(135deg, #0066CF 0%, #003366 100%);
            color: white;
            padding: 1rem 2rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }}
        
        .retry-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 102, 207, 0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI HTML Builder</h1>
            <p>Professional HTML Generation Service</p>
        </div>
        
        <div class="content">
            <div class="request-box">
                <h3>Your Request</h3>
                <div class="request-content">{user_input}</div>
            </div>
            
            <p>I'm working on creating something amazing for you! This is a temporary placeholder while I process your request with full creative attention.</p>
            
            <button class="retry-button" onclick="location.reload()">
                Try Again
            </button>
        </div>
    </div>
</body>
</html>"""


# Global conversational LLM service instance
conversational_llm_service = ConversationalLLMService()