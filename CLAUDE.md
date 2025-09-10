# AI HTML Builder - Claude Assistant Documentation

## Project Overview

This is an AI-powered web application that enables users to generate styled HTML/CSS documents through natural language chat interactions and file uploads. The system uses Anthropic's Claude Sonnet 4 to transform user inputs into professionally formatted, single-file HTML outputs with real-time preview and editing capabilities. Features include an admin dashboard, prompt templates library, and advanced session management.

## Quick Start Commands

### Development Setup
```bash
# Clone/setup project
git init
git add .
git commit -m "Initial project setup"

# Frontend setup (React 19)
cd frontend
npm install
npm run dev

# Backend setup (Python 3.11+)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Redis (via Podman/Docker)
podman run -d -p 6379:6379 --name redis redis:7-alpine
```

### Testing & Quality
```bash
# Linting & Type checking
npm run lint         # Frontend linting (in frontend/ directory)
ruff check backend/  # Python linting
mypy backend/       # Python type checking

# Build & Deploy
npm run build                        # Frontend build (in frontend/ directory)
podman build -t ai-html-builder .   # Container build
podman-compose up -d                # Deploy with compose
```

## Technology Stack (Latest Versions - 2024/2025)

### Frontend
- **React**: 19.1.1 (latest with enhanced concurrent rendering)
- **TypeScript**: 5.8.3 (latest type safety features)
- **Vite**: 7.1.2 (fast build tool with latest optimizations)
- **React Router**: 7.8.2 (modern routing solution)

### Backend
- **FastAPI**: 0.111.0+ (enhanced async features)
- **Python**: 3.11+ (balance of features and stability, 3.13 supported)
- **Redis**: 5.0.0+ (session management and caching)
- **Anthropic SDK**: 0.25.0+ (Claude Sonnet 4 integration)
- **WebSockets**: 12.0+ (real-time communication)

### Deployment
- **Podman**: Container orchestration (preferred over Docker)
- **Redis**: 7.4+ with persistence enabled

## Architecture Overview

```
Frontend (React 19) ←→ WebSocket/HTTP ←→ Backend (FastAPI)
                                              ↓
                                      Redis + Claude Sonnet 4 API
```

### Key Components
1. **Chat Interface**: Natural language processing for HTML generation with Claude Sonnet 4
2. **HTML Viewer**: Live preview with toggle between rendered/code views  
3. **File Upload**: Process .txt, .docx, .md files (50MB limit)
4. **Session Management**: Redis-based isolation (1-hour timeout)
5. **Export System**: Single-file HTML with inlined CSS/JS
6. **Admin Dashboard**: Analytics, user management, and system monitoring
7. **Prompt Templates Library**: Pre-built templates for common document types
8. **Semantic Targeting System**: Claude Artifacts-inspired precise HTML editing with surgical modifications

## System Requirements & Constraints

### Performance Targets
- **Concurrent Users**: Maximum 8 simultaneous sessions
- **Response Time**: < 10 seconds for HTML generation
- **Session Duration**: 1 hour timeout on inactivity
- **Chat Iterations**: Maximum 15 per session
- **File Size Limit**: 50MB per upload

### Design Guidelines
- **Primary Colors**: Deep Blue (#00175A), Bright Blue (#006FCF), Light Blue (#66A9E2), Charcoal (#152835), Gray 6 (#A7A8AA), White (#FFFFFF)
- **Accent Colors**: Sky Blue (#B4EEFF), Powder Blue (#F6F0FA), Yellow (#FFB900), Forest (#006469), Green (#28CD6E)
- **Fonts**: 'Benton Sans' (primary), Arial (fallback)
- **Mobile-first**: Responsive design with viewport meta tag
- **No external dependencies**: All CSS/JS must be inline

## Default Templates

### Available Templates
1. **Impact Assessment Report**: Professional report with tabbed navigation and analysis sections
2. **Technical Documentation**: Clean documentation site with sidebar navigation and code examples
3. **Business Dashboard**: Interactive dashboard with charts, metrics, and data visualization
4. **Project Report**: Structured project report with status, milestones, and team updates
5. **Process Documentation**: Step-by-step process guide with workflows and decision trees
6. **Presentation Slides**: Clean slide presentation with navigation and professional styling

### Impact Assessment Template Structure
- Blue gradient header design
- Tabbed navigation (Problem Statement, Technical Solutions, Risk Analysis, Recommendation)
- Solution cards with pros/cons sections
- Highlighted problem areas and bordered risk items
- Interactive JavaScript for tab switching
- Mobile-responsive card-based layout

## Security Best Practices

### Input Validation
- File type/size validation
- XSS prevention for text input
- HTML output sanitization
- Content Security Policy headers

### API Security
- Rate limiting: 30 requests/minute per session
- API key protection (environment variables only)
- CORS configuration with restricted origins
- No API keys exposed to client

### Session Security
- UUID v4 session generation
- Redis key prefixing for isolation
- Automatic cleanup after 1 hour
- No persistent user data storage

## Development Workflow

### Git Branch Strategy
```
main
├── develop
│   ├── feature/chat-interface
│   ├── feature/html-viewer
│   └── feature/websocket
└── release/v1.0.0
```

### Code Quality Standards
- **Frontend**: ESLint + Prettier, React best practices
- **Backend**: Ruff + MyPy, FastAPI conventions  
- **Testing**: 80%+ coverage for unit tests
- **Documentation**: Inline comments for complex logic only

### Environment Configuration
```bash
# .env file structure
ANTHROPIC_API_KEY=sk-ant-...            # Your Anthropic API key (required)
OPENAI_API_KEY=sk-...                    # Your OpenAI API key (optional, for fallback)
REDIS_URL=redis://localhost:6379         # Redis connection
ENVIRONMENT=development|production       # Environment mode
LOG_LEVEL=info                          # Logging level
MAX_UPLOAD_SIZE=52428800                # 50MB in bytes
SESSION_TIMEOUT=3600                    # 1 hour in seconds
RATE_LIMIT_REQUESTS=30                  # Per minute
RATE_LIMIT_WINDOW=60                    # Time window
CORS_ORIGINS=["http://localhost:3000"]  # Allowed origins
DEBUG=false                             # Enable debug mode
FRONTEND_URL=http://localhost:3000      # Frontend URL for development
BACKEND_URL=http://localhost:8000       # Backend URL for development
```

## System Prompts & LLM Configuration

### Claude Sonnet 4 Integration & Optimization
The system uses Anthropic's Claude Sonnet 4 (model: claude-sonnet-4-20250514) for superior HTML/CSS generation with:

#### **Core Capabilities**
- Advanced design understanding and aesthetic judgment
- Professional color palette implementation
- Modern CSS Grid and Flexbox layouts
- Accessibility-compliant markup
- Mobile-first responsive design

#### **Context Window Optimization**
- **Full Model Capacity**: 200K+ token context window
- **System Utilization**: 150K character context (75% utilization)
- **Session Support**: Handles 15 iterations with large documents
- **Intelligent Preparation**: Structure-preserving HTML context preparation
- **Performance Balance**: Optimal context size vs response time

#### **Advanced Features**
- **Semantic Analysis**: Multi-phase request understanding for targeted edits
- **Surgical Editing**: Precise modifications without content recreation
- **Preservation Intelligence**: Natural language understanding of "keep but change" requests
- **Fallback Mechanisms**: Graceful degradation when context limits approached

### Primary System Prompt Template
```markdown
You are an expert HTML/CSS developer creating single-file HTML documents with modern design principles.

REQUIREMENTS:
1. Generate complete, valid HTML5 documents
2. All CSS must be inline in <style> tags  
3. All JavaScript must be inline in <script> tags
4. No external dependencies or CDN links
5. Mobile-responsive with viewport meta tag
6. Use semantic HTML elements and ARIA attributes

DEFAULT STYLING (unless specified otherwise):
- Primary Colors: Deep Blue (#00175A), Bright Blue (#006FCF), Light Blue (#66A9E2)
- Accent Colors: Sky Blue (#B4EEFF), Yellow (#FFB900), Forest Green (#006469)
- Typography: 'Benton Sans', Arial, sans-serif with proper hierarchy
- Layout: CSS Grid/Flexbox with professional spacing
- Interactive: Smooth transitions and hover effects

OUTPUT: Return only complete HTML starting with <!DOCTYPE html>
```

### Prompt Templates Library
The system includes a comprehensive prompt templates library (see prompt_templates.md) with pre-built templates for:
- Impact Assessment Reports
- Technical Documentation
- Business Dashboards
- Project Reports
- Process Documentation
- Presentation Slides

## Semantic Targeting System (Claude Artifacts Approach)

### Overview
The system implements a sophisticated semantic targeting approach inspired by Claude Artifacts, enabling precise HTML modifications while preserving existing content and formatting. This solves the critical issue of content recreation during iterative edits.

### Architecture

```
User Request → Modification Detection → Semantic Analysis → Targeted Edit → Content Preservation
```

#### **Phase 1: Intelligent Decision Logic**
```python
# Enhanced modification detection with comprehensive keywords
modification_words = [
    "change", "modify", "update", "adjust", "fix", "edit", "improve", "enhance",
    "make", "add", "remove", "alter", "delete", "replace", "keep", "preserve"
]

# Preservation intent detection
preservation_words = [
    "keep", "preserve", "maintain", "same", "but", "except", "only", "just"
]
```

#### **Phase 2: Semantic Analysis**
The system uses Claude Sonnet 4 to analyze requests and identify:
- **TARGET_SECTIONS**: Specific HTML elements needing modification
- **CHANGE_TYPE**: content|styling|structure|addition|removal  
- **APPROACH**: targeted|full_recreation
- **REASONING**: Justification for the chosen approach

#### **Phase 3: Surgical Editing**
Based on analysis results:
- **Targeted Approach**: Extract specific sections, modify, and merge back
- **Full Context Approach**: Use enhanced 150K character context window
- **Fallback Strategy**: Standard surgical editing with preservation prompts

#### **Phase 4: Content Preservation**
Enhanced system prompts with explicit preservation instructions:
```
🚨 PRESERVE EVERYTHING EXCEPT WHAT IS EXPLICITLY REQUESTED TO CHANGE 🚨

CRITICAL PRESERVATION RULE:
- Treat the existing document as sacred
- If user says "keep everything the same but change X" - keep EVERYTHING except X
- Never recreate or restructure existing content unless explicitly asked
```

### Context Management & Performance

#### **Enhanced Context Limits**
- **Previous**: 25K characters (artificially restrictive)
- **Current**: 150K characters (75% of Claude Sonnet 4's context window)
- **Benefit**: Handles 15-iteration sessions with large documents

#### **Intelligent Context Preparation**
- Structure-preserving HTML parsing with BeautifulSoup
- Progressive content reduction maintaining DOM integrity
- Priority-based element preservation (container → header → tabs → content)
- Fallback mechanisms for context preparation failures

#### **Performance Optimizations**
- Prompt caching for repeated HTML contexts
- Semantic analysis caching for similar requests
- Efficient tokenization and context preparation
- Real-time decision logging for debugging

### Decision Flow Examples

#### Example 1: Preservation Request
```
User: "Keep everything the same but change the header title to 'New Title'"

→ Detection: ✅ Modification + Preservation intent
→ Analysis: TARGET_SECTIONS: [".header h1"], CHANGE_TYPE: content, APPROACH: targeted
→ Action: Extract header, modify title, preserve all other content
→ Result: Only title changes, everything else identical
```

#### Example 2: Complex Modification
```
User: "Add a new section after the introduction but keep all existing formatting"

→ Detection: ✅ Modification + Preservation intent  
→ Analysis: TARGET_SECTIONS: [".introduction"], CHANGE_TYPE: addition, APPROACH: targeted
→ Action: Locate insertion point, add new section, preserve existing structure
→ Result: New content added with existing formatting preserved
```

### Debugging & Monitoring

#### **Enhanced Logging**
```
[DECISION TRACKING] Message approach analysis
[CLAUDE MESSAGES] ✅ SURGICAL EDITING SELECTED - Using semantic targeting  
[SEMANTIC TARGETING] Using Claude Artifacts-inspired approach
[CLAUDE MESSAGES] 🆕 CREATION MODE SELECTED
```

#### **Key Metrics Tracked**
- Surgical vs Creation mode usage rates
- Context preparation success/failure ratios
- Semantic analysis accuracy
- Content preservation effectiveness
- Token usage optimization

### Integration Points

#### **WebSocket Handler Integration**
- Seamless integration with existing dual_response system
- Real-time progress updates during semantic analysis
- Error handling with graceful fallbacks

#### **Claude Service Integration** 
- Enhanced `_build_simple_messages()` with semantic targeting
- Improved `_parse_simple_response()` for result handling
- Optimized context limits for Claude Sonnet 4 capabilities

### Benefits

1. **Content Preservation**: Eliminates unwanted content recreation during iterations
2. **Natural Language Understanding**: Handles complex modification requests naturally
3. **Performance**: Utilizes full Claude Sonnet 4 context window efficiently
4. **Reliability**: Multiple fallback mechanisms ensure consistent operation
5. **Debugging**: Comprehensive logging for issue diagnosis and optimization

## API Documentation

### REST Endpoints
- `POST /api/upload` - File upload with validation
- `POST /api/export` - HTML export functionality  
- `GET /api/health` - System health check
- `POST /api/admin/login` - Admin authentication
- `POST /api/admin/logout` - Admin logout
- `GET /api/admin/status` - Check admin authentication status
- `GET /api/admin/verify` - Verify admin authentication
- `GET /api/admin/sessions` - Get list of all sessions with analytics
- `GET /api/admin/sessions/{session_id}` - Get detailed analytics for specific session
- `GET /api/admin/stats` - Get overall system statistics
- `GET /api/admin/overview` - Get dashboard overview with key metrics
- `DELETE /api/admin/sessions/{session_id}` - Delete analytics data for specific session

### WebSocket Protocol
- Connection: `/ws/{session_id}`
- Messages: JSON format with type, payload, timestamp
- Events: chat, update, error, status, dual_response

### Admin Features
- **Authentication**: JWT-based admin login system
- **Analytics**: Session tracking, usage metrics, performance monitoring
- **Export Management**: Bulk export functionality for generated content
- **User Management**: Session oversight and management tools

## Monitoring & Observability

### Health Checks
- Application: `/api/health` endpoint
- Redis connectivity: Ping every 30s
- Claude API: Rate limit monitoring and connection validation
- Disk space: Check `/tmp` usage
- WebSocket connections: Active session monitoring

### Key Metrics
- Request count and duration
- Active sessions and WebSocket connections
- Error rates and response times
- Claude API token usage and costs
- Admin dashboard analytics
- User engagement and session success rates

## Troubleshooting

### Common Issues
1. **WebSocket disconnections**: Automatic reconnection with exponential backoff
2. **Claude API errors**: Connection validation, retry logic with fallback prompts
3. **File upload failures**: Size/type validation, clear error messages
4. **Rate limiting**: Queue management with user feedback
5. **Session expiration**: Graceful handling with new session creation
6. **Admin authentication**: JWT token validation and refresh handling
7. **Template loading**: Prompt library initialization and caching
8. **Content preservation issues**: Semantic targeting system with surgical editing approach
9. **Context limit exceeded**: Enhanced 150K character context window with intelligent preparation
10. **Modification detection failures**: Comprehensive keyword analysis with preservation intent detection

### Performance Optimization
- Code splitting for faster initial loads
- Debouncing for editor changes (500ms)
- Virtual scrolling for long message lists
- Connection pooling for Redis (size: 20)
- Response streaming via WebSocket
- **Enhanced context management**: 150K character window utilization
- **Semantic caching**: Analysis results and HTML contexts cached
- **Surgical editing**: Targeted modifications reduce processing overhead
- **Intelligent decision logic**: Faster modification detection and routing

## Deployment Commands

### Local Development
```bash
# Start Redis
podman run -d -p 6379:6379 --name redis redis:7-alpine

# Start backend
cd backend && uvicorn app.main:app --reload

# Start frontend  
cd frontend && npm run dev
```

### Production Deployment
```bash
# Build container
podman build -t ai-html-builder .

# Deploy with compose
podman-compose up -d

# Health check
curl http://localhost:8000/api/health

# View logs
podman logs -f ai-html-builder
```

## Research & Updates

Claude is encouraged to:
- Research latest versions and best practices online
- Stay updated with technology changes and security updates
- Verify compatibility between different technology versions
- Look up current Anthropic Claude model capabilities and pricing
- Monitor OpenAI developments for potential fallback integration
- Check for breaking changes in dependencies
- Review prompt engineering best practices for Claude Sonnet 4

## Support & Maintenance

### Regular Maintenance Tasks
- Update dependencies monthly
- Review security patches
- Monitor API usage and costs  
- Clean up temporary files
- Backup Redis data (if persistence needed)

### Performance Monitoring
- P95 response time < 10 seconds
- Error rate < 1%
- 99% uptime target
- Session success rate > 90%

---

## Project Status

✅ **Completed**: 
- Core application architecture and functionality
- Claude Sonnet 4 integration with dual-response system
- Admin dashboard with authentication and comprehensive analytics
- Prompt templates library with 6 pre-built templates
- WebSocket-based real-time communication
- File upload and processing system
- Responsive React frontend with modern TypeScript
- Redis session management and caching
- Comprehensive admin API with session management, statistics, and data export
- **Semantic Targeting System**: Claude Artifacts-inspired precise HTML editing
- **Enhanced Context Management**: 150K character context window utilization
- **Intelligent Decision Logic**: Comprehensive modification detection with preservation intent
- **Surgical Editing Approach**: Targeted modifications preserving existing content
- **Advanced Logging & Debugging**: Real-time decision tracking and performance monitoring

⏳ **In Progress**: 
- Additional prompt templates and design patterns
- Extended performance metrics and optimization monitoring

🔄 **Next Steps**: 
- Production deployment optimization with semantic targeting
- Advanced caching strategies for semantic analysis results
- Extended prompt template library with more document types
- Real-time performance analytics dashboard
- A/B testing framework for surgical vs creation approaches

## Developer Notes & Implementation Guidelines

### Semantic Targeting Implementation
Key implementation details for developers working on the content preservation system:

#### **File Locations**
- **Main Logic**: `backend/app/services/claude_service.py`
- **Decision Flow**: `_build_simple_messages()` method (lines 263-320)
- **Semantic Analysis**: `_perform_semantic_targeting_edit()` method (lines 410-465)
- **Context Preparation**: `_prepare_html_for_context()` method (lines 605+)

#### **Critical Configuration Values**
```python
MAX_HTML_CONTEXT_LENGTH = 150000  # Claude Sonnet 4 optimized
OPTIMAL_CONTEXT_LENGTH = 120000   # Performance target
SURGICAL_EDITING_THRESHOLD = 2    # Simplified from 3
```

#### **Debugging Best Practices**
- Monitor `[DECISION TRACKING]` logs for approach selection
- Check `[SEMANTIC TARGETING]` logs for analysis results  
- Validate context preparation with HTML structure integrity
- Track token usage vs context preparation efficiency

#### **Performance Considerations**
- Semantic analysis adds ~1-2 seconds per targeted edit
- Context preparation scales O(n) with document size
- Cache semantic analysis results for similar requests
- Monitor Claude API token usage patterns

#### **Testing Guidelines**
Test scenarios for content preservation validation:
1. **Simple modifications**: "Change title to X"
2. **Preservation requests**: "Keep everything but change Y"  
3. **Multi-iteration sessions**: 5+ modifications on same document
4. **Large document handling**: 100K+ character HTML files
5. **Complex requests**: "Add section after intro, preserve formatting"

### Architecture Decisions

#### **Why Semantic Targeting Over Simple Surgical Editing?**
- **Problem**: Simple surgical editing fell back to creation mode too often
- **Solution**: Multi-phase analysis identifies precise change requirements
- **Benefit**: Dramatically improved content preservation success rate

#### **Why 150K Context Limit?**
- **Analysis**: Claude Sonnet 4 has 200K+ token capacity
- **Buffer**: 25% reserved for system prompts and analysis overhead
- **Performance**: Optimal balance between context size and response time
- **Scalability**: Handles 15-iteration sessions with large documents

#### **Why Dual System Prompts?**
- **Surgical Prompt**: Preservation-focused with explicit constraints
- **Creation Prompt**: Generation-focused with design guidelines
- **Benefit**: Context-appropriate instructions improve output quality

---

**Last Updated**: September 2025
**Claude Version**: Sonnet 4 (claude-sonnet-4-20250514)
**LLM Provider**: Anthropic Claude Sonnet 4 (Primary), OpenAI GPT-4 (Fallback)
**Implementation**: Semantic Targeting System with Content Preservation
**Context Optimization**: 150K character window utilization (75% of model capacity)