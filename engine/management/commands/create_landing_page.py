"""
Management command to create or update the landing page from LANDING_PAGE_CONTENT.html
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from engine.models import Page

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates or updates the default landing page from LANDING_PAGE_CONTENT.html'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing landing page instead of creating new one',
        )

    def handle(self, *args, **options):
        # Read the landing page content
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        content_file = os.path.join(base_dir, 'LANDING_PAGE_CONTENT.html')
        
        if not os.path.exists(content_file):
            self.stdout.write(
                self.style.ERROR(f'Landing page content file not found: {content_file}')
            )
            return
        
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get or create landing page
        landing_page, created = Page.objects.get_or_create(
            page_type='landing',
            is_default_landing=True,
            defaults={
                'title': 'Landing Page',
                'slug': 'landing',
                'content': content,
                'is_published': True,
                'allow_indexing': True,
                'follow_links': True,
            }
        )
        
        if not created and options['update']:
            landing_page.content = content
            landing_page.is_published = True
            landing_page.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated landing page: {landing_page.title}')
            )
        elif created:
            # Try to set created_by to first superuser
            try:
                admin_user = User.objects.filter(is_superuser=True).first()
                if admin_user:
                    landing_page.created_by = admin_user
                    landing_page.save()
            except Exception:
                pass
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created landing page: {landing_page.title}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Landing page already exists. Use --update to update it.\n'
                    f'  Title: {landing_page.title}\n'
                    f'  Slug: {landing_page.slug}\n'
                    f'  Published: {landing_page.is_published}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Landing page is ready!\n'
                '  The page will automatically display subscription plans from Admin → Subscription Plans\n'
                '  Make sure you have at least one active subscription plan created in the admin.'
            )
        )

