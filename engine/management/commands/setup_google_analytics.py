"""
Management command to set up Google Analytics in SiteSettings.
"""
from django.core.management.base import BaseCommand
from engine.models import SiteSettings


class Command(BaseCommand):
    help = 'Set up Google Analytics tracking ID or code in SiteSettings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=str,
            help='Google Analytics tracking ID (e.g., G-8FHJC3M9SD)',
        )
        parser.add_argument(
            '--code',
            type=str,
            help='Full Google Analytics code (script tags)',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable Google Analytics',
        )

    def handle(self, *args, **options):
        settings = SiteSettings.get_settings()
        
        if options['disable']:
            settings.is_active = False
            settings.save()
            self.stdout.write(
                self.style.SUCCESS('✓ Google Analytics disabled')
            )
            return
        
        if options['code']:
            settings.google_analytics_code = options['code']
            settings.google_analytics_id = None  # Clear ID if using custom code
            settings.is_active = True
            settings.save()
            self.stdout.write(
                self.style.SUCCESS('✓ Google Analytics code set (custom code)')
            )
        elif options['id']:
            settings.google_analytics_id = options['id']
            settings.google_analytics_code = None  # Clear custom code if using ID
            settings.is_active = True
            settings.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Google Analytics ID set: {options["id"]}')
            )
        else:
            # Default: Set the provided ID
            default_id = 'G-8FHJC3M9SD'
            settings.google_analytics_id = default_id
            settings.google_analytics_code = None
            settings.is_active = True
            settings.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Google Analytics ID set to default: {default_id}')
            )
            self.stdout.write(
                self.style.WARNING('  To change it, use: python manage.py setup_google_analytics --id YOUR_ID')
            )

