"""
Management command to inspect encrypted file structure.
"""
from django.core.management.base import BaseCommand
import os
import sys


class Command(BaseCommand):
    help = 'Inspect encrypted file structure and content'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to encrypted file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return
        
        file_size = os.path.getsize(file_path)
        self.stdout.write(f"\nFile: {file_path}")
        self.stdout.write(f"Size: {file_size} bytes\n")
        
        # Read first 100 bytes to inspect structure
        with open(file_path, 'rb') as f:
            first_bytes = f.read(100)
        
        self.stdout.write("First 100 bytes (hex):")
        hex_str = ' '.join(f'{b:02x}' for b in first_bytes)
        self.stdout.write(hex_str)
        
        self.stdout.write("\nFirst 100 bytes (as text, non-printable shown as '.'):")
        text_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in first_bytes)
        self.stdout.write(text_str)
        
        # Check structure
        self.stdout.write("\n" + "="*80)
        self.stdout.write("File Structure Analysis:")
        self.stdout.write("="*80)
        
        if file_size < 44:
            self.stdout.write(self.style.ERROR("❌ File is too small (minimum 44 bytes for salt + nonce + auth tag)"))
        else:
            self.stdout.write("✅ File size is above minimum")
            
            # Expected structure: 16 bytes salt + 12 bytes nonce + encrypted data
            salt = first_bytes[:16]
            nonce = first_bytes[16:28]
            encrypted_data_start = first_bytes[28:]
            
            self.stdout.write(f"\nSalt (first 16 bytes): {salt.hex()}")
            self.stdout.write(f"Nonce (next 12 bytes): {nonce.hex()}")
            self.stdout.write(f"Encrypted data starts at byte 28")
            self.stdout.write(f"Remaining data: {file_size - 28} bytes")
            
            if file_size - 28 < 16:
                self.stdout.write(self.style.WARNING("⚠️  Not enough data for even one encrypted chunk (need at least 16 bytes for auth tag)"))
            else:
                self.stdout.write("✅ Has enough data for encrypted chunks")

