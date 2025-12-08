#!/bin/bash

# Check Django startup errors

set -e

echo "🔍 Checking Django Errors"
echo "========================="
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

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "📋 Full web container logs (last 50 lines):"
echo "-------------------------------------------"
$DOCKER_COMPOSE logs --tail=50 web
echo ""

echo "🔍 Checking for common errors..."
echo ""

# Check for database connection errors
if $DOCKER_COMPOSE logs web 2>&1 | grep -qi "database\|postgres\|connection\|psycopg"; then
    echo "⚠️  Database connection issues detected!"
    echo ""
    echo "💡 Try checking:"
    echo "   1. Is PostgreSQL running? sudo systemctl status postgresql"
    echo "   2. Can you connect? psql -h localhost -U postgres -d gra"
    echo "   3. Check DB_PASSWORD in .env file"
fi

# Check for migration errors
if $DOCKER_COMPOSE logs web 2>&1 | grep -qi "migration\|migrate"; then
    echo "⚠️  Migration issues detected!"
    echo ""
    echo "💡 Try running migrations manually:"
    echo "   $DOCKER_COMPOSE run --rm web python manage.py migrate"
fi

# Check for import errors
if $DOCKER_COMPOSE logs web 2>&1 | grep -qi "import\|module\|no module"; then
    echo "⚠️  Import/module errors detected!"
    echo ""
    echo "💡 Try rebuilding the container:"
    echo "   $DOCKER_COMPOSE build web"
    echo "   $DOCKER_COMPOSE up -d web"
fi

echo ""
echo "✅ Check complete!"
