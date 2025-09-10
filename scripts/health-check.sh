#!/bin/bash

# AI HTML Builder - Production Health Check Script
# This script verifies that all services are running correctly

set -e

echo "🏥 AI HTML Builder - Health Check"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL=${BACKEND_URL:-"http://localhost:8080"}
REDIS_CONTAINER=${REDIS_CONTAINER:-"ai-html-builder-redis"}
APP_CONTAINER=${APP_CONTAINER:-"ai-html-builder-app"}

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local name=$2
    local timeout=${3:-10}
    
    echo -n "  Checking $name... "
    
    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Function to check container health
check_container() {
    local container=$1
    local name=$2
    
    echo -n "  Checking $name container... "
    
    if podman inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null | grep -q "healthy"; then
        echo -e "${GREEN}✓ HEALTHY${NC}"
        return 0
    elif podman ps --format "table {{.Names}}" | grep -q "$container"; then
        echo -e "${YELLOW}⚠ RUNNING (no health check)${NC}"
        return 0
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis() {
    echo -n "  Checking Redis connectivity... "
    
    if podman exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Main health checks
echo ""
echo "🔍 Container Health Checks:"
check_container "$REDIS_CONTAINER" "Redis"
REDIS_STATUS=$?

check_container "$APP_CONTAINER" "Application"
APP_STATUS=$?

echo ""
echo "🌐 Service Health Checks:"
check_http "$BACKEND_URL/api/health" "Backend API" 15
API_STATUS=$?

check_http "$BACKEND_URL/" "Frontend" 10
FRONTEND_STATUS=$?

echo ""
echo "💾 Database Connectivity:"
if [ $REDIS_STATUS -eq 0 ]; then
    check_redis
    REDIS_CONN_STATUS=$?
else
    echo -e "  Redis connectivity: ${RED}✗ SKIPPED (container not running)${NC}"
    REDIS_CONN_STATUS=1
fi

# Summary
echo ""
echo "📊 Health Check Summary:"
echo "========================"

TOTAL_CHECKS=5
PASSED_CHECKS=0

[ $REDIS_STATUS -eq 0 ] && ((PASSED_CHECKS++))
[ $APP_STATUS -eq 0 ] && ((PASSED_CHECKS++))
[ $API_STATUS -eq 0 ] && ((PASSED_CHECKS++))
[ $FRONTEND_STATUS -eq 0 ] && ((PASSED_CHECKS++))
[ $REDIS_CONN_STATUS -eq 0 ] && ((PASSED_CHECKS++))

echo "  Passed: $PASSED_CHECKS/$TOTAL_CHECKS"

if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
    echo -e "  Status: ${GREEN}ALL SYSTEMS HEALTHY ✓${NC}"
    echo ""
    echo "🚀 Your AI HTML Builder is ready for launch!"
    exit 0
elif [ $PASSED_CHECKS -ge 3 ]; then
    echo -e "  Status: ${YELLOW}PARTIALLY HEALTHY ⚠${NC}"
    echo ""
    echo "⚠️  Some services need attention, but core functionality should work."
    exit 1
else
    echo -e "  Status: ${RED}CRITICAL ISSUES ✗${NC}"
    echo ""
    echo "❌ Multiple services are down. Check the deployment."
    exit 2
fi