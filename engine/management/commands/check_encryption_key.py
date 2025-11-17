"""
Management command to check encryption key configuration.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from engine.encryption import get_encryption
import os


class Command(BaseCommand):
    help = 'Check encryption key configuration'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("Encryption Key Configuration Check")
        self.stdout.write("="*80 + "\n")
        
        # Check if ENCRYPTION_KEY is set
        encryption_key = os.environ.get('ENCRYPTION_KEY') or getattr(settings, 'ENCRYPTION_KEY', None)
        
        if encryption_key:
            # Show first and last few characters (for security)
            key_preview = f"{encryption_key[:8]}...{encryption_key[-8:]}" if len(encryption_key) > 16 else "***"
            self.stdout.write(f"✅ ENCRYPTION_KEY is set")
            self.stdout.write(f"   Key length: {len(encryption_key)} characters")
            self.stdout.write(f"   Key preview: {key_preview}")
        else:
            self.stdout.write(self.style.WARNING("⚠️  ENCRYPTION_KEY is NOT set"))
            self.stdout.write("   Using SECRET_KEY as fallback (not recommended for production)")
        
        # Check if using SECRET_KEY as fallback
        secret_key = getattr(settings, 'SECRET_KEY', None)
        if secret_key and not encryption_key:
            secret_preview = f"{secret_key[:8]}...{secret_key[-8:]}" if len(secret_key) > 16 else "***"
            self.stdout.write(f"   Using SECRET_KEY: {secret_preview}")
        
        # Try to get encryption instance
        try:
            enc = get_encryption()
            # Check if encryption is properly configured by trying to derive a test key
            try:
                test_salt = b'0' * 16
                test_key = enc._derive_key(test_salt, None)
                if test_key:
                    self.stdout.write(self.style.SUCCESS("\n✅ Encryption instance created successfully"))
                    self.stdout.write(f"   Key derivation working: Yes")
                else:
                    self.stdout.write(self.style.ERROR("\n❌ Encryption instance key derivation failed"))
            except Exception as derive_error:
                self.stdout.write(self.style.ERROR(f"\n❌ Key derivation failed: {derive_error}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Failed to create encryption instance: {e}"))
        
        # Check ENCRYPT_DATASETS setting
        encrypt_datasets = getattr(settings, 'ENCRYPT_DATASETS', False)
        self.stdout.write(f"\nENCRYPT_DATASETS: {'✅ Enabled' if encrypt_datasets else '⚠️  Disabled'}")
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write("Note: If decryption is failing, the file was likely encrypted")
        self.stdout.write("with a different ENCRYPTION_KEY. You need to either:")
        self.stdout.write("1. Use the original ENCRYPTION_KEY that was used when the file was uploaded")
        self.stdout.write("2. Re-upload the file with the current encryption key")
        self.stdout.write("="*80 + "\n")

