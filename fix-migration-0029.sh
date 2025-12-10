#!/bin/bash

# Fix missing migration 0029 issue

echo "🔧 Fixing migration 0029 issue..."
echo ""

cd ~/GRA || cd ~/statbox || { echo "❌ Could not find project directory"; exit 1; }

echo "1. Checking if migration 0029 file exists..."
if [ -f "engine/migrations/0029_alter_subscriptionplan_options_and_more.py" ]; then
    echo "✅ Migration 0029 file exists"
else
    echo "❌ Migration 0029 file is missing"
    echo "Creating placeholder migration..."
    
    cat > engine/migrations/0029_alter_subscriptionplan_options_and_more.py << 'EOF'
# Dummy migration to resolve missing 0029 reference
# This migration was created on the server but the file was lost
# It's a placeholder to satisfy migration 0036's dependency

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0028_merge_subscription_models"),
    ]

    operations = [
        # This is a placeholder migration - no operations
        # The actual changes were likely already applied to the database
    ]
EOF
    echo "✅ Created placeholder migration 0029"
fi

echo ""
echo "2. Checking migration status in database..."
docker-compose exec -T web python manage.py showmigrations engine | grep -E "0028|0029|0030|0035|0036" || echo "Could not check migrations"

echo ""
echo "3. If migration 0029 is already applied in database but file was missing:"
echo "   We can fake it (mark as applied without running)"
echo ""
read -p "Do you want to fake migration 0029? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Faking migration 0029..."
    docker-compose exec -T web python manage.py migrate engine 0029 --fake || \
    docker-compose run --rm web python manage.py migrate engine 0029 --fake
    echo "✅ Migration 0029 faked"
fi

echo ""
echo "4. Running migrations..."
docker-compose run --rm web python manage.py migrate || \
docker-compose exec -T web python manage.py migrate

echo ""
echo "5. Checking migration status..."
docker-compose exec -T web python manage.py showmigrations engine | tail -10

echo ""
echo "6. Restarting web container..."
docker-compose restart web

echo ""
echo "7. Checking web logs..."
sleep 5
docker-compose logs --tail=15 web | tail -15

echo ""
echo "📋 Summary:"
echo "==========="
echo "✅ Created placeholder migration 0029"
echo "✅ This should resolve the NodeNotFoundError"
echo ""
echo "If you still see errors, the database may have migration 0029 applied"
echo "but with different content. In that case, you may need to:"
echo "1. Check what migrations are actually applied: docker-compose exec web python manage.py showmigrations"
echo "2. Fake the migration: docker-compose exec web python manage.py migrate engine 0029 --fake"
echo "3. Then run migrations: docker-compose exec web python manage.py migrate"
