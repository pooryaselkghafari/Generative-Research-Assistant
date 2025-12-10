#!/bin/bash

# Complete fix for DB_USER issue - ensures it's set correctly everywhere

echo "🔧 Complete fix for DB_USER issue..."
echo ""

cd ~/GRA || { echo "❌ Not in GRA directory"; exit 1; }

echo "1. Checking current .env file..."
if [ -f .env ]; then
    echo "Current DB_USER in .env:"
    grep "^DB_USER=" .env || echo "DB_USER not found in .env"
else
    echo "❌ .env file not found!"
    exit 1
fi
echo ""

echo "2. Fixing .env file..."
# Backup
cp .env .env.backup.$(date +%s)

# Fix DB_USER
sed -i 's/^DB_USER=.*/DB_USER=postgres/' .env
sed -i 's/^DB_NAME=.*/DB_NAME=statbox/' .env

# Verify
echo "Updated settings:"
grep -E "^DB_USER=|^DB_NAME=" .env
echo ""

echo "3. Checking docker-compose.yml for hardcoded values..."
if grep -q "DB_USER.*adminpoorya" docker-compose.yml; then
    echo "⚠️  Found hardcoded DB_USER in docker-compose.yml!"
    echo "Fixing docker-compose.yml..."
    sed -i 's/DB_USER.*adminpoorya/DB_USER=${DB_USER:-postgres}/' docker-compose.yml
fi
echo ""

echo "4. Stopping web container to ensure clean restart..."
docker-compose stop web
echo ""

echo "5. Checking database container..."
docker-compose ps db
if ! docker-compose ps db | grep -q "Up"; then
    echo "Starting database..."
    docker-compose up -d db
    sleep 10
fi
echo ""

echo "6. Verifying database port is exposed..."
if ss -tlnp 2>/dev/null | grep -q ":5432" || netstat -tlnp 2>/dev/null | grep -q ":5432"; then
    echo "✅ Port 5432 is listening"
else
    echo "❌ Port 5432 not listening - checking docker-compose.yml..."
    if ! grep -q "127.0.0.1:5432:5432" docker-compose.yml; then
        echo "Adding port configuration..."
        # This is a bit complex, so we'll do it manually
        echo "⚠️  Please manually add 'ports: - \"127.0.0.1:5432:5432\"' to db section in docker-compose.yml"
    fi
fi
echo ""

echo "7. Recreating web container to pick up new environment variables..."
docker-compose up -d --force-recreate web
echo ""

echo "8. Waiting for container to start..."
sleep 5

echo ""
echo "9. Checking environment variables inside container..."
docker-compose exec -T web env | grep -E "DB_USER|DB_NAME|DB_HOST" | head -5
echo ""

echo "10. Checking web container logs..."
docker-compose logs --tail=20 web | tail -20

echo ""
echo "📋 Summary:"
echo "==========="
echo "✅ Fixed .env file: DB_USER=postgres"
echo "✅ Recreated web container"
echo ""
echo "If you still see 'adminpoorya' in logs, check:"
echo "1. .env file: cat .env | grep DB_USER"
echo "2. Container env: docker-compose exec web env | grep DB_USER"
echo "3. docker-compose.yml for any hardcoded values"
