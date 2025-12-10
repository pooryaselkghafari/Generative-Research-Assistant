#!/bin/bash

# Fix duplicate column error - column already exists in database

echo "🔧 Fixing duplicate column error..."
echo ""

cd ~/GRA || { echo "❌ Not in GRA directory"; exit 1; }

echo "1. Checking which migrations are applied..."
docker-compose exec -T web python manage.py showmigrations engine 2>/dev/null | grep -E "0030|0029|0028" || echo "Could not check"

echo ""
echo "2. The error shows 'updated_at' column already exists."
echo "   This means migration 0030 was partially applied or the column was added manually."
echo ""

echo "3. Option 1: Fake migration 0030 (mark as applied without running)"
echo "   This is safe if the column already exists..."
read -p "Fake migration 0030? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Faking migration 0030..."
    docker-compose exec -T web python manage.py migrate engine 0030 --fake 2>/dev/null || \
    docker-compose run --rm web python manage.py migrate engine 0030 --fake
    echo "✅ Migration 0030 faked"
fi

echo ""
echo "4. Running remaining migrations..."
docker-compose run --rm web python manage.py migrate 2>&1 | tail -20

echo ""
echo "5. If still getting errors, we can modify migration 0030 to check if column exists first..."
echo "   This requires editing the migration file to add a check."

echo ""
echo "6. Restarting web container..."
docker-compose restart web

echo ""
echo "7. Checking logs..."
sleep 5
docker-compose logs --tail=15 web | tail -15

echo ""
echo "📋 Alternative fix if faking doesn't work:"
echo "=========================================="
echo "Edit migration 0030 to check if column exists:"
echo ""
echo "  nano engine/migrations/0030_add_updated_at_to_subscriptionplan.py"
echo ""
echo "Wrap the AddField operation in a check, or use RunPython to verify column exists first."
