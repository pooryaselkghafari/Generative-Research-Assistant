#!/bin/bash

# Fix 500 error on login page

echo "🔧 Diagnosing and fixing login 500 error..."
echo ""

cd ~/GRA || { echo "❌ Not in GRA directory"; exit 1; }

echo "1. Checking web container logs for login errors..."
docker-compose logs --tail=50 web | grep -i -A 10 -B 5 "login\|error\|traceback" | tail -30
echo ""

echo "2. Checking if accounts migrations are applied..."
docker-compose exec -T web python manage.py showmigrations accounts 2>/dev/null | tail -10 || echo "Could not check migrations"
echo ""

echo "3. Running accounts migrations (if needed)..."
docker-compose run --rm web python manage.py migrate accounts 2>&1 | tail -10
echo ""

echo "4. Checking if static files are collected..."
if docker-compose exec -T web test -d /app/staticfiles 2>/dev/null; then
    echo "✅ Static files directory exists"
    FILE_COUNT=$(docker-compose exec -T web find /app/staticfiles -type f 2>/dev/null | wc -l)
    echo "   Found $FILE_COUNT static files"
    if [ "$FILE_COUNT" -lt 10 ]; then
        echo "⚠️  Very few static files - collecting them..."
        docker-compose run --rm web python manage.py collectstatic --noinput 2>&1 | tail -10
    fi
else
    echo "⚠️  Static files not collected - collecting now..."
    docker-compose run --rm web python manage.py collectstatic --noinput 2>&1 | tail -10
fi
echo ""

echo "5. Testing login page directly..."
echo "   (This will show any Python errors)"
docker-compose run --rm web python manage.py shell << 'PYEOF'
from django.test import Client
from django.urls import reverse

try:
    client = Client()
    response = client.get('/accounts/login/')
    print(f"Status code: {response.status_code}")
    if response.status_code == 500:
        print("❌ 500 error on login page")
        # Try to get the error
        try:
            print("Error details:", str(response.content)[:500])
        except:
            pass
    else:
        print("✅ Login page loads successfully")
except Exception as e:
    print(f"❌ Error testing login: {e}")
    import traceback
    traceback.print_exc()
PYEOF

echo ""
echo "6. Checking for common configuration issues..."
echo "   - Google OAuth settings (if using Google login)"
grep -E "GOOGLE_OAUTH|SITE_ID" .env 2>/dev/null | head -3 || echo "   Not found in .env"
echo ""

echo "7. Checking Django settings for login configuration..."
docker-compose run --rm web python manage.py shell << 'PYEOF'
from django.conf import settings
try:
    print(f"LOGIN_URL: {getattr(settings, 'LOGIN_URL', 'Not set')}")
    print(f"SITE_ID: {getattr(settings, 'SITE_ID', 'Not set')}")
    print(f"ACCOUNT_EMAIL_VERIFICATION: {getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION', 'Not set')}")
except Exception as e:
    print(f"Error checking settings: {e}")
PYEOF

echo ""
echo "8. Restarting web container..."
docker-compose restart web

echo ""
echo "9. Waiting and checking latest logs..."
sleep 5
docker-compose logs --tail=20 web | tail -20

echo ""
echo "📋 Common fixes for login 500 errors:"
echo "====================================="
echo "1. Run all migrations: docker-compose run --rm web python manage.py migrate"
echo "2. Collect static files: docker-compose run --rm web python manage.py collectstatic --noinput"
echo "3. Check .env has SITE_ID=1 (required for allauth)"
echo "4. Check web container logs for specific error: docker-compose logs web | grep -A 20 'Traceback'"
echo "5. Test login view: curl http://localhost:8000/accounts/login/"
