#!/bin/bash
# Backup script for n8n data and AgentTemplate database

set -e

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
N8N_BACKUP_FILE="${BACKUP_DIR}/n8n_backup_${DATE}.tar.gz"
DB_BACKUP_FILE="${BACKUP_DIR}/agent_templates_${DATE}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting n8n backup at $(date)"

# Backup n8n data volume (if accessible)
if docker volume inspect n8n_data > /dev/null 2>&1; then
    echo "Backing up n8n data volume..."
    docker run --rm \
        -v n8n_data:/data \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf "/backup/n8n_backup_${DATE}.tar.gz" -C /data .
    echo "n8n data backed up to: $N8N_BACKUP_FILE"
else
    echo "Warning: n8n_data volume not found, skipping n8n data backup"
fi

# Backup AgentTemplate table from database
if command -v pg_dump > /dev/null 2>&1; then
    echo "Backing up AgentTemplate database table..."
    export PGPASSWORD="${DB_PASSWORD}"
    pg_dump -h "${DB_HOST:-localhost}" \
            -U "${DB_USER:-postgres}" \
            -d "${DB_NAME:-gra}" \
            -t engine_agenttemplate \
            > "$DB_BACKUP_FILE"
    echo "Database backed up to: $DB_BACKUP_FILE"
else
    echo "Warning: pg_dump not found, skipping database backup"
fi

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "n8n_backup_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "agent_templates_*.sql" -mtime +30 -delete

echo "Backup completed at $(date)"

