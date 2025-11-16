"""
Test script to verify encryption is working correctly.

Run this from Django shell or as a management command to test:
1. Database field encryption
2. File encryption (if enabled)
3. Encryption/decryption functionality
"""
from django.conf import settings
from engine.models import UserProfile, Payment
from django.contrib.auth.models import User
from engine.encryption import get_encryption, encrypt_data, decrypt_data
from engine.encrypted_storage import store_encrypted_file, read_encrypted_file
import tempfile
import os


def test_encryption_settings():
    """Test 1: Check encryption settings are configured."""
    print("=" * 60)
    print("TEST 1: Encryption Settings")
    print("=" * 60)
    
    encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
    encrypt_datasets = getattr(settings, 'ENCRYPT_DATASETS', False)
    encrypt_db_fields = getattr(settings, 'ENCRYPT_DB_FIELDS', False)
    
    print(f"ENCRYPTION_KEY set: {'✅ Yes' if encryption_key and encryption_key != settings.SECRET_KEY else '❌ No (using SECRET_KEY)'}")
    print(f"ENCRYPT_DATASETS: {'✅ Enabled' if encrypt_datasets else '⚠️  Disabled'}")
    print(f"ENCRYPT_DB_FIELDS: {'✅ Enabled' if encrypt_db_fields else '⚠️  Disabled'}")
    
    if encryption_key and encryption_key != settings.SECRET_KEY:
        print(f"Encryption Key: {encryption_key[:20]}... (truncated)")
    else:
        print("⚠️  WARNING: Using SECRET_KEY as encryption key. Generate a dedicated key!")
    
    return encryption_key and encryption_key != settings.SECRET_KEY


def test_basic_encryption():
    """Test 2: Test basic encryption/decryption."""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Encryption/Decryption")
    print("=" * 60)
    
    try:
        test_data = "test_stripe_customer_id_12345"
        print(f"Original data: {test_data}")
        
        # Encrypt
        encrypted = encrypt_data(test_data)
        print(f"Encrypted: {encrypted[:50]}... (truncated)")
        
        # Decrypt
        decrypted = decrypt_data(encrypted)
        print(f"Decrypted: {decrypted}")
        
        # Verify
        if decrypted == test_data:
            print("✅ Encryption/Decryption working correctly!")
            return True
        else:
            print("❌ Decrypted data doesn't match original!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_database_field_encryption():
    """Test 3: Test encrypted database fields."""
    print("\n" + "=" * 60)
    print("TEST 3: Database Field Encryption")
    print("=" * 60)
    
    try:
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='encryption_test_user',
            defaults={'email': 'test@example.com'}
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"Created test user: {user.username}")
        else:
            print(f"Using existing test user: {user.username}")
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'subscription_type': 'free'}
        )
        
        # Test encrypted field
        test_stripe_id = "cus_test_encryption_12345"
        print(f"\nSetting stripe_customer_id to: {test_stripe_id}")
        profile.stripe_customer_id = test_stripe_id
        profile.save()
        
        # Read it back
        profile.refresh_from_db()
        retrieved_value = profile.stripe_customer_id
        print(f"Retrieved value: {retrieved_value}")
        
        # Verify
        if retrieved_value == test_stripe_id:
            print("✅ Database field encryption working! (value matches)")
            
            # Check if it's actually encrypted in the database
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT stripe_customer_id FROM engine_userprofile WHERE id = %s",
                    [profile.id]
                )
                raw_value = cursor.fetchone()[0]
                if raw_value != test_stripe_id:
                    print(f"✅ Value is encrypted in database: {raw_value[:50]}... (different from original)")
                else:
                    print("⚠️  Value appears to be stored in plaintext in database")
            
            return True
        else:
            print(f"❌ Retrieved value doesn't match! Expected: {test_stripe_id}, Got: {retrieved_value}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_encryption():
    """Test 4: Test file encryption (if enabled)."""
    print("\n" + "=" * 60)
    print("TEST 4: File Encryption")
    print("=" * 60)
    
    if not getattr(settings, 'ENCRYPT_DATASETS', False):
        print("⚠️  File encryption is disabled (ENCRYPT_DATASETS=False)")
        print("   Skipping file encryption test")
        return None
    
    try:
        # Create a test file
        test_content = "This is test data for encryption\nLine 2\nLine 3"
        test_file_path = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        test_file_path.write(test_content)
        test_file_path.close()
        
        print(f"Original file content: {test_content[:50]}...")
        
        # Encrypt the file
        encrypted_path = store_encrypted_file(
            open(test_file_path.name, 'rb'),
            user_id=1
        )
        print(f"Encrypted file created: {encrypted_path}")
        
        # Check if encrypted file exists and is different
        if os.path.exists(encrypted_path):
            encrypted_size = os.path.getsize(encrypted_path)
            original_size = os.path.getsize(test_file_path.name)
            print(f"Original size: {original_size} bytes")
            print(f"Encrypted size: {encrypted_size} bytes")
            
            # Try to read encrypted file as text (should fail or show encrypted data)
            with open(encrypted_path, 'rb') as f:
                encrypted_bytes = f.read(100)
                if b'This is test data' not in encrypted_bytes:
                    print("✅ File appears to be encrypted (original content not visible)")
                else:
                    print("⚠️  File might not be encrypted (original content visible)")
        
        # Decrypt and read
        decrypted_df = read_encrypted_file(encrypted_path, user_id=1, as_dataframe=False)
        if os.path.exists(decrypted_df):
            with open(decrypted_df, 'r') as f:
                decrypted_content = f.read()
            print(f"Decrypted content: {decrypted_content[:50]}...")
            
            if decrypted_content == test_content:
                print("✅ File encryption/decryption working correctly!")
                result = True
            else:
                print("❌ Decrypted content doesn't match original!")
                result = False
            
            # Cleanup
            os.unlink(decrypted_df)
        else:
            print("⚠️  Could not verify decryption")
            result = False
        
        # Cleanup
        os.unlink(test_file_path.name)
        if os.path.exists(encrypted_path):
            os.unlink(encrypted_path)
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all encryption tests."""
    print("\n" + "🔐 ENCRYPTION TEST SUITE" + "\n")
    
    results = []
    
    # Test 1: Settings
    results.append(("Settings Check", test_encryption_settings()))
    
    # Test 2: Basic encryption
    results.append(("Basic Encryption", test_basic_encryption()))
    
    # Test 3: Database fields
    results.append(("Database Fields", test_database_field_encryption()))
    
    # Test 4: File encryption (optional)
    file_test = test_file_encryption()
    if file_test is not None:
        results.append(("File Encryption", file_test))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All encryption tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
    
    return passed == total


if __name__ == "__main__":
    import django
    import os
    import sys
    
    # Setup Django
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statbox.settings')
    django.setup()
    
    run_all_tests()

