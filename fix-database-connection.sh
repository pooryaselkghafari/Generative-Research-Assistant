#!/bin/bash

# Fix database connection issue
# This script exposes the database port and restarts services

echo "🔧 Fixing database connection..."
echo ""

cd ~/GRA || cd ~/statbox || { echo "❌ Could not find project directory"; exit 1; }

echo "1. Checking docker-compose.yml..."
if grep -q "127.0.0.1:5432:5432" docker-compose.yml; then
    echo "✅ Database port is already exposed"
else
    echo "⚠️  Database port not exposed. Updating docker-compose.yml..."
    # This should be done by pulling latest code, but we can do it manually
    sed -i 's/# ports:/ports:/' docker-compose.yml
    sed -i 's/#   - "127.0.0.1:5432:5432"/  - "127.0.0.1:5432:5432"/' docker-compose.yml
    echo "✅ Updated docker-compose.yml"
fi

echo ""
echo "2. Checking database container status..."
docker-compose ps db

echo ""
echo "3. Restarting database container to apply port changes..."
docker-compose up -d db

echo ""
echo "4. Waiting for database to be ready..."
sleep 10

echo ""
echo "5. Testing database connection..."
if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "⚠️  Database may still be starting, waiting a bit more..."
    sleep 5
fi

echo ""
echo "6. Checking if port 5432 is listening on host..."
if ss -tlnp 2>/dev/null | grep -q ":5432" || netstat -tlnp 2>/dev/null | grep -q ":5432"; then
    echo "✅ Port 5432 is listening"
    ss -tlnp 2>/dev/null | grep ":5432" || netstat -tlnp 2>/dev/null | grep ":5432"
else
    echo "❌ Port 5432 is not listening"
    echo "   Database container may not have started properly"
    echo "   Check logs: docker-compose logs db"
fi

echo ""
echo "7. Restarting web container..."
docker-compose restart web

echo ""
echo "8. Waiting for web container to start..."
sleep 5

echo ""
echo "9. Checking web container logs..."
docker-compose logs --tail=20 web | tail -20

echo ""
echo "10. Testing Django connection..."
sleep 2
if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Django is responding!"
    echo ""
    echo "🌍 Your site should now be accessible!"
else
    echo "⚠️  Django is not responding yet"
    echo ""
    echo "Check logs: docker-compose logs web"
fi

echo ""
echo "📋 Summary:"
echo "==========="
echo "Database should be accessible at: localhost:5432"
echo "Web container (using host network) should connect to: localhost:5432"
echo ""
echo "If still having issues:"
echo "1. Check .env file has correct DB_PASSWORD"
echo "2. Verify DB_NAME matches (should be 'statbox')"
echo "3. Check database logs: docker-compose logs db"
echo "4. Test connection: docker-compose exec db psql -U postgres -d statbox"
