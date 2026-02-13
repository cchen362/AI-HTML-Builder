#!/bin/bash
set -e

BACKUP_DIR="backups"
DB_PATH="data/app.db"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    cp "$DB_PATH" "$BACKUP_DIR/app_${TIMESTAMP}.db"
    gzip "$BACKUP_DIR/app_${TIMESTAMP}.db"
    echo "Backed up to $BACKUP_DIR/app_${TIMESTAMP}.db.gz"
else
    echo "No database found at $DB_PATH"
fi

# Clean old backups
find "$BACKUP_DIR" -name "*.db.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
echo "Cleaned backups older than $RETENTION_DAYS days"
