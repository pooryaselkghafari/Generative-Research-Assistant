"""
Management command to check migration status and provide guidance.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Check migration status and database schema'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if updated_at column exists in subscriptionplan table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='engine_subscriptionplan' 
                AND column_name='updated_at'
            """)
            has_updated_at = cursor.fetchone() is not None
            
            # Check if new fields exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='engine_subscriptionplan' 
                AND column_name IN ('max_datasets', 'max_sessions', 'max_file_size_mb', 'workflow_template_id')
            """)
            new_fields = [row[0] for row in cursor.fetchall()]
            
            self.stdout.write("=" * 60)
            self.stdout.write("Migration Status Check")
            self.stdout.write("=" * 60)
            
            if has_updated_at:
                self.stdout.write(self.style.SUCCESS("✓ updated_at column exists"))
            else:
                self.stdout.write(self.style.ERROR("✗ updated_at column does NOT exist"))
                self.stdout.write(self.style.WARNING("  → Run: python manage.py migrate engine"))
            
            if new_fields:
                self.stdout.write(self.style.SUCCESS(f"✓ New fields exist: {', '.join(new_fields)}"))
            else:
                self.stdout.write(self.style.ERROR("✗ New fields do NOT exist"))
                self.stdout.write(self.style.WARNING("  → Run: python manage.py migrate engine"))
            
            self.stdout.write("=" * 60)

