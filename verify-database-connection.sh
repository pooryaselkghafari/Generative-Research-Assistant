#!/bin/bash

# Verify and fix database connection

echo "🔍 Diagnosing database connection issue..."
echo ""

cd ~/GRA || cd ~/statbox || { echo "❌ Could not find project directory"; exit 1; }

echo "1. Checking database container status..."
docker-compose ps db
echo ""

echo "2. Checking if database port is exposed in docker-compose.yml..."
if grep -q "127.0.0.1:5432:5432" docker-compose.yml; then
    echo "✅ Port is configured in docker-compose.yml"
else
    echo "❌ Port is NOT configured!"
    echo ""
    echo "Fixing docker-compose.yml..."
    # Find the db section and uncomment/add ports
    sed -i '/^  db:/,/^  [a-z]/ {
        /# ports:/s/# ports:/ports:/
        /#   - "127.0.0.1:5432:5432"/s/#   - "127.0.0.1:5432:5432"/  - "127.0.0.1:5432:5432"/
    }' docker-compose.yml
    
    # Alternative: use a more robust approach
    python3 << 'PYEOF'
import re

with open('docker-compose.yml', 'r') as f:
    content = f.read()

# Check if ports are already there
if '127.0.0.1:5432:5432' in content and 'ports:' in content:
    print("Ports already configured")
else:
    # Find db section and add ports
    pattern = r'(  db:.*?POSTGRES_PASSWORD: \$\{DB_PASSWORD\})(.*?)(\n  [a-z]|\n\n)'
    
    replacement = r'\1\n    # Expose port to host so web container can access it\n    ports:\n      - "127.0.0.1:5432:5432"\2\3'
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open('docker-compose.yml', 'w') as f:
        f.write(content)
    print("✅ Added port configuration to docker-compose.yml")
PYEOF
fi
echo ""

echo "3. Checking if port 5432 is listening on host..."
if ss -tlnp 2>/dev/null | grep -q ":5432" || netstat -tlnp 2>/dev/null | grep -q ":5432"; then
    echo "✅ Port 5432 is listening"
    ss -tlnp 2>/dev/null | grep ":5432" || netstat -tlnp 2>/dev/null | grep ":5432"
else
    echo "❌ Port 5432 is NOT listening"
    echo ""
    echo "Database container may need to be restarted to apply port changes"
fi
echo ""

echo "4. Restarting database container..."
docker-compose down db
docker-compose up -d db

echo ""
echo "5. Waiting for database to start..."
sleep 15

echo ""
echo "6. Checking database container logs..."
docker-compose logs --tail=10 db

echo ""
echo "7. Testing database connection from host..."
if command -v psql &> /dev/null; then
    PGPASSWORD=${DB_PASSWORD:-$(grep DB_PASSWORD .env 2>/dev/null | cut -d'=' -f2)} psql -h localhost -U postgres -d statbox -c "SELECT 1;" 2>&1 | head -5
else
    echo "psql not installed, testing with docker..."
    docker-compose exec -T db psql -U postgres -d statbox -c "SELECT 1;" 2>&1 | head -5
fi
echo ""

echo "8. Checking if port 5432 is now listening..."
if ss -tlnp 2>/dev/null | grep -q ":5432" || netstat -tlnp 2>/dev/null | grep -q ":5432"; then
    echo "✅ Port 5432 is now listening!"
    ss -tlnp 2>/dev/null | grep ":5432" || netstat -tlnp 2>/dev/null | grep ":5432"
else
    echo "❌ Port 5432 is still not listening"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check database container: docker-compose ps db"
    echo "2. Check database logs: docker-compose logs db"
    echo "3. Verify .env has DB_PASSWORD set"
    echo "4. Try: docker-compose restart db"
fi
echo ""

echo "9. Restarting web container..."
docker-compose restart web

echo ""
echo "10. Waiting and checking web logs..."
sleep 5
docker-compose logs --tail=15 web | tail -15

echo ""
echo "📋 Summary:"
echo "==========="
echo "If port 5432 is listening, the web container should be able to connect."
echo "If not, check:"
echo "  - Database container is running: docker-compose ps db"
echo "  - Database logs for errors: docker-compose logs db"
echo "  - .env file has DB_PASSWORD: grep DB_PASSWORD .env"
