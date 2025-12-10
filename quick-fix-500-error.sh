#!/bin/bash

# Quick fix for 500 error - fixes logging issue immediately

echo "🔧 Quick fix for 500 Server Error..."
echo ""

cd ~/GRA || cd ~/statbox || { echo "❌ Could not find project directory"; exit 1; }

echo "1. Fixing logs directory permissions..."
mkdir -p logs
chmod 755 logs
touch logs/django.log 2>/dev/null
chmod 644 logs/django.log 2>/dev/null

# Fix ownership
CURRENT_USER=${SUDO_USER:-$USER}
chown -R $CURRENT_USER:$CURRENT_USER logs/ 2>/dev/null

echo "✅ Logs directory fixed"
echo ""

echo "2. Fixing permissions inside container..."
docker-compose exec -u root web chown -R appuser:appuser /app/logs 2>/dev/null || \
docker-compose run --rm -u root web chown -R appuser:appuser /app/logs 2>/dev/null || \
echo "⚠️  Could not fix permissions in container (will try alternative fix)"

echo ""

echo "3. Quick fix: Temporarily remove file handler from settings.py..."
SETTINGS_FILE="statbox/settings.py"

if [ -f "$SETTINGS_FILE" ]; then
    # Backup
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup.$(date +%s)"
    
    # Remove file handler from handlers list
    sed -i "s/'file', 'console'/'console'/g" "$SETTINGS_FILE"
    sed -i "s/'console', 'file'/'console'/g" "$SETTINGS_FILE"
    sed -i "s/\['file', 'console'\]/\['console'\]/g" "$SETTINGS_FILE"
    sed -i "s/\['console', 'file'\]/\['console'\]/g" "$SETTINGS_FILE"
    
    # Remove file handler definition (between 'file': { and },)
    python3 << 'PYEOF'
import re

with open('statbox/settings.py', 'r') as f:
    content = f.read()

# Remove file handler definition
content = re.sub(r"'file':\s*\{[^}]*\},?\s*", "", content, flags=re.DOTALL)

with open('statbox/settings.py', 'w') as f:
    f.write(content)
PYEOF

    echo "✅ Settings.py updated (file handler removed)"
else
    echo "⚠️  Settings.py not found"
fi

echo ""

echo "4. Restarting web container..."
docker-compose restart web

echo ""
echo "5. Waiting for container to start..."
sleep 5

echo ""
echo "6. Checking status..."
docker-compose ps web

echo ""
echo "7. Checking logs..."
docker-compose logs --tail=10 web | tail -10

echo ""
echo "8. Testing connection..."
sleep 2
if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Django is responding!"
    echo ""
    echo "🌍 Your site should now be accessible at:"
    echo "   http://generativera.com"
    echo "   https://generativera.com"
else
    echo "❌ Still not responding. Checking logs for errors..."
    echo ""
    docker-compose logs --tail=20 web | grep -i error
    echo ""
    echo "📋 Try these steps:"
    echo "   1. Check full logs: docker-compose logs web"
    echo "   2. Pull latest code: git pull && docker-compose build web"
    echo "   3. Check .env file: cat .env | grep SECRET_KEY"
fi
