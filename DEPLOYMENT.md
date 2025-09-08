# AI HTML Builder - Podman Deployment Guide

This guide covers deploying the AI HTML Builder with admin analytics dashboard using Podman containers.

## Prerequisites

- Podman installed on your system
- Podman Compose (or Docker Compose with Podman)
- Your API keys for Claude (Anthropic) and optionally OpenAI

## Quick Start with Podman

### 1. Clone and Setup

```bash
git clone <your-repository>
cd AI-HTML-Builder
```

### 2. Configure Environment

Create a `.env.prod` file with your production settings:

```bash
# API Keys (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here

# Admin Authentication
JWT_SECRET=your-very-secure-jwt-secret-key-here
ADMIN_PASSWORD=your-secure-admin-password

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=info
MAX_UPLOAD_SIZE=52428800
SESSION_TIMEOUT=3600

# Rate Limiting
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Redis Configuration
REDIS_URL=redis://redis:6379

# URLs (adjust for your domain)
FRONTEND_URL=https://your-domain.com
BACKEND_URL=https://your-domain.com
```

### 3. Build and Deploy

```bash
# Build the application image
podman build -t ai-html-builder:latest .

# Start with Podman Compose
podman-compose -f docker-compose.prod.yml up -d

# Or manually start containers
podman network create ai-html-builder

# Start Redis
podman run -d \
  --name ai-html-builder-redis \
  --network ai-html-builder \
  -v redis_data:/data \
  redis:7.4-alpine redis-server --appendonly yes

# Start Application
podman run -d \
  --name ai-html-builder-app \
  --network ai-html-builder \
  -p 8080:8000 \
  --env-file .env.prod \
  ai-html-builder:latest
```

### 4. Access Your Application

- **Main App**: http://your-server:8080
- **Admin Dashboard**: http://your-server:8080/admin
- **Admin Login**: Use password: `adminhtml` (or your custom password)

## Admin Dashboard Features

### 🔐 Secure Access
- Password-protected admin login
- JWT-based session management
- 8-hour session timeout

### 📊 Analytics Tracking
- Response times (Claude API + processing)
- Token usage (input/output tracking)
- Session iterations and user input analysis
- Output type classification (landing-page, documentation, newsletter, etc.)

### 📈 Dashboard Overview
- Total sessions and activity metrics
- Popular output types
- Success rates and performance stats
- Recent session activity

### 📋 Data Export
- CSV export with date filtering
- Detailed analytics events
- Session summaries
- Compatible with Excel/Google Sheets

## Container Management

### Health Checks
```bash
# Check application health
podman exec ai-html-builder-app python -c "import requests; print(requests.get('http://localhost:8000/api/health').json())"

# Check Redis
podman exec ai-html-builder-redis redis-cli ping

# View logs
podman logs ai-html-builder-app
podman logs ai-html-builder-redis
```

### Updates and Maintenance
```bash
# Update application
git pull
podman build -t ai-html-builder:latest .
podman-compose -f docker-compose.prod.yml up -d --force-recreate app

# Backup Redis data
podman exec ai-html-builder-redis redis-cli BGSAVE

# Clean up old images
podman image prune -f
```

### Scaling and Performance
```bash
# Monitor resource usage
podman stats

# Scale Redis memory (if needed)
podman exec ai-html-builder-redis redis-cli CONFIG SET maxmemory 512mb
podman exec ai-html-builder-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Production Configuration

### Reverse Proxy (Recommended)

Use Nginx or Traefik to handle HTTPS and domain routing:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Security Best Practices

1. **Change Default Password**: Update `ADMIN_PASSWORD` in production
2. **Secure JWT Secret**: Use a strong, unique `JWT_SECRET`
3. **HTTPS Only**: Use TLS/SSL in production
4. **Firewall Rules**: Restrict access to admin routes
5. **Regular Updates**: Keep containers and dependencies updated

### Monitoring

```bash
# Application logs
podman logs -f ai-html-builder-app

# Resource monitoring
watch podman stats

# Health endpoints
curl http://localhost:8080/api/health
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" http://localhost:8080/api/admin/stats
```

## Analytics Data Management

### Data Retention
- Analytics events: 7 days (configurable via Redis TTL)
- Session data: 1 hour timeout (configurable)
- Logs: Managed by container runtime

### CSV Export Examples
- **Last 7 days**: Detailed analytics with response times, tokens, output types
- **Session summaries**: High-level performance metrics per session
- **Custom date ranges**: Filter exports by specific time periods

### Tracked Metrics
- ⏱️ **Response Times**: Total processing time and Claude API-specific timing
- 🎯 **Token Usage**: Input, output, and total token consumption
- 🔄 **Iterations**: Number of chat exchanges per session
- 🎨 **Output Types**: Auto-classification (landing-page, documentation, newsletter, etc.)
- ✅ **Success Rates**: Error tracking and completion statistics

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   podman exec ai-html-builder-app python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"
   ```

2. **Admin Login Issues**
   - Verify `JWT_SECRET` is set
   - Check admin password configuration
   - Review browser cookies and CORS settings

3. **Analytics Not Recording**
   - Confirm Redis is running and connected
   - Check application logs for analytics errors
   - Verify WebSocket connections are working

4. **Export Failures**
   - Ensure sufficient disk space
   - Check file permissions
   - Verify date range parameters

### Container Troubleshooting
```bash
# Enter container for debugging
podman exec -it ai-html-builder-app /bin/bash

# Check environment variables
podman exec ai-html-builder-app env | grep -E "(REDIS|JWT|API)"

# Test Redis connectivity
podman exec ai-html-builder-redis redis-cli info
```

## Support

For issues and feature requests, check:
- Application logs: `podman logs ai-html-builder-app`
- Health endpoint: `/api/health`
- Admin dashboard: `/admin` (with proper authentication)

---

**Security Note**: This deployment includes admin analytics with password protection. Ensure you change the default admin password and use HTTPS in production environments.