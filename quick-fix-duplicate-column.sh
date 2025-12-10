#!/bin/bash

# Quick fix for duplicate column error

echo "🔧 Quick fix for duplicate column 'updated_at'..."
echo ""

cd ~/GRA || { echo "❌ Not in GRA directory"; exit 1; }

echo "The 'updated_at' column already exists in the database."
echo "We'll fake migration 0030 to mark it as applied."
echo ""

echo "1. Faking migration 0030 (marking as applied without running)..."
docker-compose exec -T web python manage.py migrate engine 0030 --fake 2>/dev/null || \
docker-compose run --rm web python manage.py migrate engine 0030 --fake

if [ $? -eq 0 ]; then
    echo "✅ Migration 0030 faked successfully"
else
    echo "⚠️  Could not fake migration, trying alternative..."
fi
echo ""

echo "2. Running remaining migrations..."
docker-compose run --rm web python manage.py migrate 2>&1 | tail -20

echo ""
echo "3. If you still get duplicate column errors, we need to:"
echo "   - Either fake more migrations that try to add existing columns"
echo "   - Or modify the migration files to check if columns exist first"
echo ""

echo "4. Restarting web container..."
docker-compose restart web

echo ""
echo "5. Checking logs..."
sleep 5
docker-compose logs --tail=15 web | tail -15

echo ""
echo "📋 If errors persist:"
echo "===================="
echo "Check which migrations are applied:"
echo "  docker-compose exec web python manage.py showmigrations engine"
echo ""
echo "Fake any migrations that try to add columns that already exist:"
echo "  docker-compose exec web python manage.py migrate engine <migration_number> --fake"
