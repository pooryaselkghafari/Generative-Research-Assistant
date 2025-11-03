"""
Django management command to generate a secure encryption key.
Usage: python manage.py generate_encryption_key
"""

from django.core.management.base import BaseCommand
import secrets
import base64


class Command(BaseCommand):
    help = 'Generate a secure 256-bit encryption key for data encryption'

    def handle(self, *args, **options):
        # Generate 32 random bytes (256 bits) for AES-256
        key_bytes = secrets.token_bytes(32)
        
        # Encode as base64 for easy storage
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('ENCRYPTION KEY GENERATED')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60 + '\n')
        )
        self.stdout.write(key_b64)
        self.stdout.write(
            self.style.WARNING('\n⚠️  IMPORTANT: Store this key securely!')
        )
        self.stdout.write(
            self.style.WARNING('Add it to your .env file as:')
        )
        self.stdout.write(
            self.style.SUCCESS(f'ENCRYPTION_KEY={key_b64}\n')
        )
        self.stdout.write(
            self.style.WARNING('NEVER commit this key to version control!\n')
        )


