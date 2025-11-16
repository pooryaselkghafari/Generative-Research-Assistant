"""
Django management command to create Privacy Policy and Terms of Service documents.

Usage: python manage.py create_legal_documents
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from engine.models import PrivacyPolicy, TermsOfService
from datetime import date
import os


class Command(BaseCommand):
    help = 'Create Privacy Policy and Terms of Service documents from template files'

    def handle(self, *args, **options):
        """Create legal documents."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Creating Legal Documents")
        self.stdout.write("=" * 60 + "\n")
        
        # Get base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Read privacy policy content
        privacy_file = os.path.join(base_dir, 'PRIVACY_POLICY_CONTENT.html')
        if os.path.exists(privacy_file):
            with open(privacy_file, 'r', encoding='utf-8') as f:
                privacy_content = f.read()
            
            # Create or update privacy policy
            policy, created = PrivacyPolicy.objects.get_or_create(
                version='1.0',
                defaults={
                    'content': privacy_content,
                    'effective_date': date.today(),
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing
                policy.content = privacy_content
                policy.effective_date = date.today()
                policy.is_active = True
                policy.save()
                self.stdout.write(self.style.SUCCESS("✅ Updated Privacy Policy v1.0"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Created Privacy Policy v1.0"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  Privacy policy template not found at: {privacy_file}"))
        
        # Read terms of service content
        terms_file = os.path.join(base_dir, 'TERMS_OF_SERVICE_CONTENT.html')
        if os.path.exists(terms_file):
            with open(terms_file, 'r', encoding='utf-8') as f:
                terms_content = f.read()
            
            # Create or update terms of service
            terms, created = TermsOfService.objects.get_or_create(
                version='1.0',
                defaults={
                    'content': terms_content,
                    'effective_date': date.today(),
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing
                terms.content = terms_content
                terms.effective_date = date.today()
                terms.is_active = True
                terms.save()
                self.stdout.write(self.style.SUCCESS("✅ Updated Terms of Service v1.0"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Created Terms of Service v1.0"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  Terms of service template not found at: {terms_file}"))
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Legal documents created successfully!"))
        self.stdout.write("=" * 60 + "\n")
        self.stdout.write("You can now view them at:")
        self.stdout.write("  - Privacy Policy: /privacy/")
        self.stdout.write("  - Terms of Service: /terms/")
        self.stdout.write("\nTo edit them, go to Django Admin > Privacy Policies or Terms of Service\n")

