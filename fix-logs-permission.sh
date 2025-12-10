#!/bin/bash

# Fix logs directory permission issue
# Run this script to create the logs directory with proper permissions

echo "🔧 Fixing logs directory permissions..."

# Get the current user
CURRENT_USER=${SUDO_USER:-$USER}
CURRENT_UID=$(id -u $CURRENT_USER)
CURRENT_GID=$(id -g $CURRENT_USER)

# Create logs directory if it doesn't exist
mkdir -p logs

# Set proper ownership (match current user)
chown -R $CURRENT_UID:$CURRENT_GID logs 2>/dev/null || chown -R $CURRENT_USER:$CURRENT_USER logs 2>/dev/null

# Set proper permissions (read/write/execute for owner, read for others)
chmod 755 logs

# Create django.log file if it doesn't exist (with proper permissions)
touch logs/django.log
chown $CURRENT_UID:$CURRENT_GID logs/django.log 2>/dev/null || chown $CURRENT_USER:$CURRENT_USER logs/django.log 2>/dev/null
chmod 644 logs/django.log

# If running in Docker, also fix permissions inside container
if command -v docker-compose &> /dev/null; then
    echo ""
    echo "🐳 Fixing permissions in Docker container..."
    # Try to fix permissions inside the container
    docker-compose exec -T web chown -R appuser:appuser /app/logs 2>/dev/null || \
    docker-compose run --rm --user root web chown -R appuser:appuser /app/logs 2>/dev/null || \
    echo "⚠️  Could not fix permissions in container (container may not be running)"
fi

echo ""
echo "✅ Logs directory created and permissions set!"
echo ""
echo "📋 Next steps:"
echo "1. If using Docker, rebuild your container:"
echo "   docker-compose build web"
echo ""
echo "2. Restart services:"
echo "   docker-compose up -d"
echo ""
echo "3. If still having issues, check permissions:"
echo "   ls -la logs/"
echo "   docker-compose exec web ls -la /app/logs"
echo ""
