#!/bin/bash
# Script to check admin security configuration

echo "=========================================="
echo "ADMIN SECURITY CONFIGURATION CHECK"
echo "=========================================="
echo ""

# Check .env file
if [ -f .env ]; then
    echo "✓ .env file exists"
    echo ""
    echo "Current settings:"
    grep -E "ADMIN_URL|ADMIN_ALLOWED_IPS|ADMIN_ACCESS_TOKEN|ADMIN_HIDE" .env | sed 's/=.*/=***HIDDEN***/' || echo "  No admin settings found in .env"
else
    echo "✗ .env file not found!"
fi

echo ""
echo "=========================================="
echo "Testing Django Settings"
echo "=========================================="

docker-compose exec web python manage.py shell << 'EOF'
from django.conf import settings
import os

print(f"ADMIN_URL: {getattr(settings, 'ADMIN_URL', 'NOT SET')}")
print(f"ADMIN_ALLOWED_IPS: {getattr(settings, 'ADMIN_ALLOWED_IPS', [])}")
print(f"ADMIN_ACCESS_TOKEN set: {'YES (hidden)' if getattr(settings, 'ADMIN_ACCESS_TOKEN', None) else 'NO'}")
print(f"ADMIN_HIDE_FROM_UNAUTHORIZED: {getattr(settings, 'ADMIN_HIDE_FROM_UNAUTHORIZED', 'NOT SET')}")
print("")
print("Expected admin URL:")
admin_url = getattr(settings, 'ADMIN_URL', 'whereadmingoeshere')
print(f"  https://yourdomain.com/{admin_url}/?token=YOUR_ACTUAL_TOKEN")
EOF

echo ""
echo "=========================================="
echo "To generate a token, run:"
echo "  openssl rand -hex 32"
echo "=========================================="

