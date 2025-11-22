#!/bin/bash
# Script to verify and set up Google Analytics

echo "=========================================="
echo "GOOGLE ANALYTICS SETUP VERIFICATION"
echo "=========================================="
echo ""

echo "Step 1: Checking if migrations are run..."
docker-compose exec web python manage.py showmigrations engine | grep "0024_add_site_settings" || echo "  ⚠ Migration not applied yet"

echo ""
echo "Step 2: Checking current SiteSettings..."
docker-compose exec web python manage.py shell << 'EOF'
from engine.models import SiteSettings

try:
    settings = SiteSettings.get_settings()
    print(f"  ✓ SiteSettings exists")
    print(f"  Is Active: {settings.is_active}")
    print(f"  Google Analytics ID: {settings.google_analytics_id or 'NOT SET'}")
    print(f"  Google Analytics Code: {'SET' if settings.google_analytics_code else 'NOT SET'}")
    
    if not settings.is_active:
        print("\n  ⚠ Google Analytics is DISABLED")
    elif not settings.google_analytics_id and not settings.google_analytics_code:
        print("\n  ⚠ Google Analytics ID/Code is NOT SET")
    else:
        print("\n  ✓ Google Analytics is configured")
except Exception as e:
    print(f"  ✗ Error: {e}")
EOF

echo ""
echo "Step 3: Setting up Google Analytics..."
echo "  Running: setup_google_analytics --id G-8FHJC3M9SD"
docker-compose exec web python manage.py setup_google_analytics --id G-8FHJC3M9SD

echo ""
echo "Step 4: Verifying setup..."
docker-compose exec web python manage.py shell << 'EOF'
from engine.models import SiteSettings

settings = SiteSettings.get_settings()
print(f"  Final Status:")
print(f"  Is Active: {settings.is_active}")
print(f"  Google Analytics ID: {settings.google_analytics_id}")
print(f"  Google Analytics Code: {'SET' if settings.google_analytics_code else 'NOT SET'}")
EOF

echo ""
echo "=========================================="
echo "Next Steps:"
echo "1. Restart web service: docker-compose restart web"
echo "2. Visit your site and check page source (Ctrl+U)"
echo "3. Look for 'googletagmanager.com' in the HTML"
echo "4. Check Google Analytics Real-time reports"
echo "=========================================="

