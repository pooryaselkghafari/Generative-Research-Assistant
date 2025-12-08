#!/bin/bash

# Fix nginx upstream to work with host network mode web container

set -e

echo "🔧 Fixing nginx upstream configuration..."
echo ""

# Find project directory
if [ -d ~/GRA1 ]; then
    PROJECT_DIR=~/GRA1
elif [ -d ~/GRA ]; then
    PROJECT_DIR=~/GRA
elif [ -d /home/deploy/GRA1 ]; then
    PROJECT_DIR=/home/deploy/GRA1
elif [ -d /home/deploy/GRA ]; then
    PROJECT_DIR=/home/deploy/GRA
else
    echo "❌ Could not find project directory."
    exit 1
fi

cd "$PROJECT_DIR"

# Get Docker bridge gateway IP
DOCKER_GATEWAY=$(docker network inspect bridge 2>/dev/null | grep -oP '"Gateway": "\K[^"]+' | head -1 || echo "172.17.0.1")

echo "📋 Docker bridge gateway: $DOCKER_GATEWAY"
echo ""

# Update nginx.conf to use the correct upstream
if [ -f nginx.conf ]; then
    # Backup
    cp nginx.conf nginx.conf.backup
    
    # Replace upstream django section
    sed -i "s|server 172.17.0.1:8000;|server $DOCKER_GATEWAY:8000;|g" nginx.conf
    
    # Also replace any web:8000 references
    sed -i "s|web:8000|$DOCKER_GATEWAY:8000|g" nginx.conf
    
    echo "✅ Updated nginx.conf upstream to use $DOCKER_GATEWAY:8000"
    echo ""
    
    # Test nginx config
    echo "🧪 Testing nginx configuration..."
    if docker compose exec nginx nginx -t 2>/dev/null || docker-compose exec nginx nginx -t 2>/dev/null; then
        echo "✅ Nginx configuration is valid"
    else
        echo "⚠️  Could not test nginx config (container may not be running)"
    fi
    echo ""
    
    # Restart nginx
    echo "🔄 Restarting nginx..."
    docker compose restart nginx 2>/dev/null || docker-compose restart nginx
    echo "✅ Nginx restarted"
else
    echo "❌ nginx.conf not found!"
    exit 1
fi

echo ""
echo "✅ Fix complete!"
