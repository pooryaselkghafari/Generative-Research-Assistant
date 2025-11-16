#!/usr/bin/env python
"""
Quick encryption test script - can be run directly on server.

Usage: python quick_encryption_test.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statbox.settings')
django.setup()

from django.conf import settings
from engine.models import UserProfile
from django.contrib.auth.models import User
from engine.encryption import encrypt_data, decrypt_data

print("\n" + "=" * 60)
print("🔐 QUICK ENCRYPTION TEST")
print("=" * 60)

# Test 1: Settings
print("\n1. Checking Settings...")
encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
encrypt_db_fields = getattr(settings, 'ENCRYPT_DB_FIELDS', False)

if encryption_key and encryption_key != settings.SECRET_KEY:
    print("   ✅ ENCRYPTION_KEY is set")
    print(f"   Key preview: {encryption_key[:30]}...")
else:
    print("   ❌ ENCRYPTION_KEY not set or using SECRET_KEY")
    print("   Run: python manage.py generate_encryption_key")

print(f"   ENCRYPT_DB_FIELDS: {'✅ Enabled' if encrypt_db_fields else '⚠️  Disabled'}")

# Test 2: Basic encryption
print("\n2. Testing Basic Encryption...")
try:
    test_data = "test_stripe_id_12345"
    encrypted = encrypt_data(test_data)
    decrypted = decrypt_data(encrypted)
    
    if decrypted == test_data:
        print("   ✅ Encryption/Decryption working!")
        print(f"   Original: {test_data}")
        print(f"   Encrypted: {encrypted[:50]}...")
    else:
        print("   ❌ Decryption failed - values don't match")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Database field
print("\n3. Testing Database Field Encryption...")
try:
    user = User.objects.first()
    if not user:
        print("   ⚠️  No users found - create a user first")
    else:
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'subscription_type': 'free'}
        )
        
        test_id = "cus_test_encryption_12345"
        profile.stripe_customer_id = test_id
        profile.save()
        
        profile.refresh_from_db()
        retrieved = profile.stripe_customer_id
        
        if retrieved == test_id:
            print("   ✅ Database field encryption working!")
            print(f"   Stored and retrieved: {retrieved}")
            
            # Check raw DB value
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT stripe_customer_id FROM engine_userprofile WHERE id = %s",
                    [profile.id]
                )
                raw = cursor.fetchone()[0]
                if raw and raw != test_id:
                    print(f"   ✅ Value is encrypted in DB: {raw[:50]}...")
                else:
                    print("   ⚠️  Value might be plaintext in DB")
        else:
            print(f"   ❌ Mismatch! Expected: {test_id}, Got: {retrieved}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60 + "\n")

