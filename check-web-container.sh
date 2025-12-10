#!/bin/bash

# Check why web container is not listening on port 8000

echo "🔍 Diagnosing web container issue..."
echo ""

# Check if web container is actually running
echo "1. Container status:"
docker-compose ps web
echo ""

# Check web container logs
echo "2. Recent web container logs (last 50 lines):"
echo "=============================================="
docker-compose logs --tail=50 web
echo ""

# Check if process is running inside container
echo "3. Processes inside web container:"
docker-compose exec web ps aux 2>/dev/null || echo "⚠️  Cannot exec into container - it may have crashed"
echo ""

# Check if port 8000 is bound
echo "4. Checking if port 8000 is listening:"
docker-compose exec web netstat -tlnp 2>/dev/null | grep 8000 || \
docker-compose exec web ss -tlnp 2>/dev/null | grep 8000 || \
echo "❌ Port 8000 is not listening inside container"
echo ""

# Check environment variables
echo "5. Checking critical environment variables:"
docker-compose exec web env | grep -E "SECRET_KEY|DEBUG|DB_|ALLOWED_HOSTS" | head -10
echo ""

# Try to start web container manually to see errors
echo "6. Attempting to start web container and capture output:"
echo "========================================================"
docker-compose up web 2>&1 | head -30
echo ""

echo "📋 Recommendations:"
echo "==================="
echo ""
echo "If you see errors above, common fixes:"
echo ""
echo "1. Missing or incorrect .env file:"
echo "   - Make sure .env exists in project root"
echo "   - Check SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS are set"
echo ""
echo "2. Logs directory permissions:"
echo "   ./fix-logs-permission.sh"
echo ""
echo "3. Database not ready:"
echo "   docker-compose up -d db"
echo "   sleep 10"
echo "   docker-compose up -d web"
echo ""
echo "4. Check Django can start:"
echo "   docker-compose run --rm web python manage.py check"
echo ""
