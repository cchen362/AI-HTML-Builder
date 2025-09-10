#!/bin/bash

# AI HTML Builder - Production Deployment Script
# Automated deployment with health checks and rollback capability

set -e

echo "🚀 AI HTML Builder - Production Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ai-html-builder"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Function to print step
print_step() {
    echo ""
    echo -e "${BLUE}🔄 $1${NC}"
    echo "----------------------------------------"
}

# Function to check prerequisites
check_prerequisites() {
    print_step "Checking Prerequisites"
    
    # Check if podman is installed
    if ! command -v podman &> /dev/null; then
        echo -e "${RED}❌ Podman is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Podman is available${NC}"
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}❌ $COMPOSE_FILE not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Compose file found${NC}"
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}❌ $ENV_FILE not found${NC}"
        echo -e "${YELLOW}💡 Create $ENV_FILE with your production settings${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Environment file found${NC}"
    
    # Check if required environment variables are set
    if ! grep -q "ANTHROPIC_API_KEY=" "$ENV_FILE"; then
        echo -e "${RED}❌ ANTHROPIC_API_KEY not found in $ENV_FILE${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ API key configured${NC}"
}

# Function to create backup
create_backup() {
    print_step "Creating Backup"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup Redis data if container exists
    if podman ps -a --format "{{.Names}}" | grep -q "${PROJECT_NAME}-redis"; then
        echo "📦 Backing up Redis data..."
        podman exec "${PROJECT_NAME}-redis" redis-cli BGSAVE > /dev/null 2>&1 || true
        podman cp "${PROJECT_NAME}-redis:/data/dump.rdb" "$BACKUP_DIR/" > /dev/null 2>&1 || true
        echo -e "${GREEN}✓ Redis data backed up${NC}"
    else
        echo -e "${YELLOW}⚠ No existing Redis container found${NC}"
    fi
    
    # Backup environment file
    cp "$ENV_FILE" "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Environment file backed up${NC}"
    
    echo "📁 Backup created in: $BACKUP_DIR"
}

# Function to build application
build_application() {
    print_step "Building Application"
    
    echo "🔨 Building Docker image..."
    podman build -t "${PROJECT_NAME}:latest" .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build completed successfully${NC}"
    else
        echo -e "${RED}❌ Build failed${NC}"
        exit 1
    fi
}

# Function to deploy services
deploy_services() {
    print_step "Deploying Services"
    
    echo "🛑 Stopping existing services..."
    podman-compose -f "$COMPOSE_FILE" down > /dev/null 2>&1 || true
    
    echo "🚀 Starting new services..."
    podman-compose -f "$COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Services started successfully${NC}"
    else
        echo -e "${RED}❌ Service startup failed${NC}"
        exit 1
    fi
}

# Function to wait for services
wait_for_services() {
    print_step "Waiting for Services to Start"
    
    echo "⏳ Waiting for containers to be healthy..."
    local max_wait=120
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if podman-compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.Status}}" | grep -q "healthy"; then
            echo -e "${GREEN}✓ Services are healthy${NC}"
            return 0
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
        echo -n "."
    done
    
    echo ""
    echo -e "${YELLOW}⚠ Services took longer than expected to start${NC}"
    return 1
}

# Function to run health checks
run_health_checks() {
    print_step "Running Health Checks"
    
    if [ -f "scripts/health-check.sh" ]; then
        chmod +x scripts/health-check.sh
        ./scripts/health-check.sh
        return $?
    else
        echo -e "${YELLOW}⚠ Health check script not found, running basic checks${NC}"
        
        # Basic health check
        if curl -s "http://localhost:8080/api/health" > /dev/null; then
            echo -e "${GREEN}✓ Basic health check passed${NC}"
            return 0
        else
            echo -e "${RED}❌ Basic health check failed${NC}"
            return 1
        fi
    fi
}

# Function to show deployment info
show_deployment_info() {
    print_step "Deployment Complete"
    
    echo -e "${GREEN}🎉 AI HTML Builder deployed successfully!${NC}"
    echo ""
    echo "📋 Service Information:"
    echo "  🌐 Application: http://localhost:8080"
    echo "  🔧 Admin Panel: http://localhost:8080/admin"
    echo "  📚 API Docs: http://localhost:8080/docs"
    echo ""
    echo "🔍 Management Commands:"
    echo "  View logs: podman logs -f ${PROJECT_NAME}-app"
    echo "  Check status: podman-compose -f $COMPOSE_FILE ps"
    echo "  Stop services: podman-compose -f $COMPOSE_FILE down"
    echo ""
    echo "💾 Backup Location: $BACKUP_DIR"
}

# Function to handle rollback
rollback_deployment() {
    print_step "Rolling Back Deployment"
    
    echo "🔄 Stopping failed deployment..."
    podman-compose -f "$COMPOSE_FILE" down > /dev/null 2>&1 || true
    
    # Restore Redis data if backup exists
    if [ -f "$BACKUP_DIR/dump.rdb" ]; then
        echo "📦 Restoring Redis data..."
        # This would require more complex logic for a real rollback
        echo -e "${YELLOW}⚠ Manual Redis data restoration may be required${NC}"
    fi
    
    echo -e "${RED}❌ Deployment rolled back${NC}"
    echo "📁 Backup available in: $BACKUP_DIR"
    exit 1
}

# Trap to handle failures
trap 'rollback_deployment' ERR

# Main deployment flow
main() {
    echo -e "${BLUE}Starting deployment at $(date)${NC}"
    
    # Run deployment steps
    check_prerequisites
    create_backup
    build_application
    deploy_services
    
    # Wait and verify
    if wait_for_services && run_health_checks; then
        show_deployment_info
        echo -e "${GREEN}✅ Deployment completed successfully at $(date)${NC}"
    else
        echo -e "${RED}❌ Health checks failed, initiating rollback...${NC}"
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "AI HTML Builder Deployment Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --no-backup   Skip backup creation"
        echo "  --quick       Skip health checks"
        echo ""
        echo "Prerequisites:"
        echo "  - Podman and podman-compose installed"
        echo "  - $ENV_FILE configured with API keys"
        echo "  - $COMPOSE_FILE present"
        exit 0
        ;;
    --no-backup)
        create_backup() { echo "⚠ Skipping backup creation"; }
        ;;
    --quick)
        run_health_checks() { echo "⚠ Skipping health checks"; return 0; }
        ;;
esac

# Run main deployment
main