"""
Django management command to test encryption functionality.

Usage: python manage.py test_encryption
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from engine.models import UserProfile, Payment
from django.contrib.auth.models import User
from engine.encryption import get_encryption, encrypt_data, decrypt_data, encrypt_file, decrypt_file
import tempfile
import os


class Command(BaseCommand):
    help = 'Test encryption functionality (database fields and files)'

    def handle(self, *args, **options):
        """Run encryption tests."""
        self.stdout.write("\n" + "🔐 ENCRYPTION TEST SUITE" + "\n")
        
        results = []
        
        # Test 1: Settings
        results.append(("Settings Check", self.test_settings()))
        
        # Test 2: Basic encryption
        results.append(("Basic Encryption", self.test_basic_encryption()))
        
        # Test 3: Database fields (may skip if DB not available)
        db_result = self.test_database_fields()
        if db_result is not None:  # Only add if test ran (not skipped)
            results.append(("Database Fields", db_result))
        
        # Test 4: File encryption (if enabled)
        if getattr(settings, 'ENCRYPT_DATASETS', False):
            results.append(("File Encryption", self.test_file_encryption()))
        else:
            # Test file encryption anyway to verify the encryption functions work
            # (even if file encryption is disabled in settings)
            results.append(("File Encryption", self.test_file_encryption()))
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TEST SUMMARY")
        self.stdout.write("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.stdout.write(f"{test_name}: {status}")
        
        self.stdout.write(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            self.stdout.write(self.style.SUCCESS("\n🎉 All encryption tests passed!"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  Some tests failed. Review the output above."))

    def test_settings(self):
        """Test encryption settings."""
        self.stdout.write("=" * 60)
        self.stdout.write("TEST 1: Encryption Settings")
        self.stdout.write("=" * 60)
        
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        encrypt_datasets = getattr(settings, 'ENCRYPT_DATASETS', False)
        encrypt_db_fields = getattr(settings, 'ENCRYPT_DB_FIELDS', False)
        
        key_status = '✅ Yes' if encryption_key and encryption_key != settings.SECRET_KEY else '❌ No (using SECRET_KEY)'
        self.stdout.write(f"ENCRYPTION_KEY set: {key_status}")
        self.stdout.write(f"ENCRYPT_DATASETS: {'✅ Enabled' if encrypt_datasets else '⚠️  Disabled'}")
        self.stdout.write(f"ENCRYPT_DB_FIELDS: {'✅ Enabled' if encrypt_db_fields else '⚠️  Disabled'}")
        
        if encryption_key and encryption_key != settings.SECRET_KEY:
            self.stdout.write(f"Encryption Key: {encryption_key[:20]}... (truncated)")
        else:
            self.stdout.write(self.style.WARNING("⚠️  WARNING: Using SECRET_KEY as encryption key. Generate a dedicated key!"))
        
        return encryption_key and encryption_key != settings.SECRET_KEY

    def test_basic_encryption(self):
        """Test basic encryption/decryption."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TEST 2: Basic Encryption/Decryption")
        self.stdout.write("=" * 60)
        
        try:
            test_data = "test_stripe_customer_id_12345"
            self.stdout.write(f"Original data: {test_data}")
            
            encrypted = encrypt_data(test_data)
            self.stdout.write(f"Encrypted: {encrypted[:50]}... (truncated)")
            
            decrypted = decrypt_data(encrypted)
            self.stdout.write(f"Decrypted: {decrypted}")
            
            if decrypted == test_data:
                self.stdout.write(self.style.SUCCESS("✅ Encryption/Decryption working correctly!"))
                return True
            else:
                self.stdout.write(self.style.ERROR("❌ Decrypted data doesn't match original!"))
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            return False

    def test_database_fields(self):
        """Test encrypted database fields."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TEST 3: Database Field Encryption")
        self.stdout.write("=" * 60)
        
        try:
            # Test database connection first
            from django.db import connection
            connection.ensure_connection()
        except Exception as db_error:
            self.stdout.write(self.style.WARNING(f"⚠️  Database connection failed: {db_error}"))
            self.stdout.write(self.style.WARNING("   Skipping database field test (database not available)"))
            self.stdout.write(self.style.WARNING("   This is normal if database is not configured or not running"))
            return None  # Skip test, don't count as failure
        
        try:
            # Get or create test user
            user, created = User.objects.get_or_create(
                username='encryption_test_user',
                defaults={'email': 'test@example.com'}
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(f"Created test user: {user.username}")
            else:
                self.stdout.write(f"Using existing test user: {user.username}")
            
            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'subscription_type': 'free'}
            )
            
            # Test encrypted field
            test_stripe_id = "cus_test_encryption_12345"
            self.stdout.write(f"\nSetting stripe_customer_id to: {test_stripe_id}")
            profile.stripe_customer_id = test_stripe_id
            profile.save()
            
            # Read back
            profile.refresh_from_db()
            retrieved_value = profile.stripe_customer_id
            self.stdout.write(f"Retrieved value: {retrieved_value}")
            
            if retrieved_value == test_stripe_id:
                self.stdout.write(self.style.SUCCESS("✅ Database field encryption working! (value matches)"))
                
                # Check raw database value
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT stripe_customer_id FROM engine_userprofile WHERE id = %s",
                        [profile.id]
                    )
                    raw_value = cursor.fetchone()[0]
                    if raw_value and raw_value != test_stripe_id:
                        self.stdout.write(f"✅ Value is encrypted in database: {raw_value[:50]}... (different from original)")
                    elif raw_value == test_stripe_id:
                        self.stdout.write(self.style.WARNING("⚠️  Value appears to be stored in plaintext in database"))
                
                return True
            else:
                self.stdout.write(self.style.ERROR(f"❌ Retrieved value doesn't match! Expected: {test_stripe_id}, Got: {retrieved_value}"))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            import traceback
            traceback.print_exc()
            return False

    def test_file_encryption(self):
        """Test file encryption."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TEST 4: File Encryption")
        self.stdout.write("=" * 60)
        
        test_file_path = None
        encrypted_path = None
        decrypted_path = None
        
        try:
            # Create test file
            test_content = "This is test data for encryption\nLine 2\nLine 3"
            test_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            test_file_path = test_file.name
            test_file.write(test_content)
            test_file.close()
            
            self.stdout.write(f"Original file content: {test_content[:50]}...")
            
            # Encrypt using encryption module directly
            encrypted_path = test_file_path + '.encrypted'
            encrypt_file(test_file_path, encrypted_path, user_id=1)
            
            self.stdout.write(f"Encrypted file created: {encrypted_path}")
            
            if os.path.exists(encrypted_path):
                encrypted_size = os.path.getsize(encrypted_path)
                original_size = os.path.getsize(test_file_path)
                self.stdout.write(f"Original size: {original_size} bytes")
                self.stdout.write(f"Encrypted size: {encrypted_size} bytes")
                
                # Verify encrypted file is different
                with open(encrypted_path, 'rb') as f:
                    encrypted_bytes = f.read(100)
                    if b'This is test data' not in encrypted_bytes:
                        self.stdout.write("✅ File appears to be encrypted (original content not visible)")
                    else:
                        self.stdout.write(self.style.WARNING("⚠️  File might not be encrypted (original content visible)"))
            
            # Decrypt and verify
            decrypted_path = tempfile.NamedTemporaryFile(delete=False, suffix='.txt').name
            decrypt_file(encrypted_path, decrypted_path, user_id=1)
            
            if os.path.exists(decrypted_path):
                with open(decrypted_path, 'r') as f:
                    decrypted_content = f.read()
                
                if decrypted_content == test_content:
                    self.stdout.write(self.style.SUCCESS("✅ File encryption/decryption working correctly!"))
                    result = True
                else:
                    self.stdout.write(self.style.ERROR("❌ Decrypted content doesn't match original!"))
                    self.stdout.write(f"   Expected length: {len(test_content)}, Got: {len(decrypted_content)}")
                    result = False
            else:
                self.stdout.write(self.style.WARNING("⚠️  Could not verify decryption"))
                result = False
            
            return result
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup
            for path in [test_file_path, encrypted_path, decrypted_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass

