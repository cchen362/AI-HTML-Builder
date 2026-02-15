#!/bin/bash
set -e

echo "=== AI HTML Builder - Deploy ==="

# Check prerequisites
if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod not found. Copy .env.example to .env.prod and add API keys."
    exit 1
fi

# Backup databases if they exist
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
if [ -f data/app.db ]; then
    cp data/app.db "backups/app_${TIMESTAMP}.db"
    echo "Database backed up to backups/app_${TIMESTAMP}.db"
fi
if [ -f data/auth.db ]; then
    cp data/auth.db "backups/auth_${TIMESTAMP}.db"
    echo "Auth database backed up to backups/auth_${TIMESTAMP}.db"
fi

# Pull latest code
if [ -d .git ]; then
    echo "Pulling latest..."
    git pull origin main
fi

# Build and start
echo "Building image..."
docker compose build

echo "Starting container..."
docker compose up -d

# Wait for health
echo "Waiting for health check..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:6669/api/health > /dev/null 2>&1; then
        echo ""
        echo "=== Healthy! ==="
        docker compose ps
        echo ""
        echo "Direct:  http://100.94.82.35:6669"
        echo "Domain:  https://clhtml.zyroi.com"
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "ERROR: Health check failed after 60s"
docker compose logs --tail=50
exit 1
