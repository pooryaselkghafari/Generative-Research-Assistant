"""
Management command to test email configuration.
Usage: python manage.py test_email your-email@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import smtplib


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send test email to')
        parser.add_argument('--verbose', action='store_true', help='Show detailed connection info')

    def handle(self, *args, **options):
        email = options['email']
        verbose = options.get('verbose', False)
        
        self.stdout.write(self.style.WARNING('Testing email configuration...'))
        
        # Display current email settings
        if verbose:
            self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
            self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
            self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
            self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
            self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            self.stdout.write(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
            self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
            self.stdout.write(f"EMAIL_TIMEOUT: {getattr(settings, 'EMAIL_TIMEOUT', 'NOT SET')}")
            self.stdout.write("")
        
        # Test SMTP connection
        self.stdout.write("Testing SMTP connection...")
        try:
            # Port 465 uses SSL, port 587 uses TLS
            if getattr(settings, 'EMAIL_USE_SSL', False):
                # Port 465: Use SMTP_SSL (SSL from the start)
                server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=getattr(settings, 'EMAIL_TIMEOUT', 10))
            elif getattr(settings, 'EMAIL_USE_TLS', False):
                # Port 587: Use STARTTLS
                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=getattr(settings, 'EMAIL_TIMEOUT', 10))
                server.starttls()
            else:
                # No encryption (not recommended)
                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=getattr(settings, 'EMAIL_TIMEOUT', 10))
            
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                self.stdout.write(self.style.SUCCESS('✓ SMTP connection successful'))
            else:
                self.stdout.write(self.style.WARNING('⚠ No credentials provided, skipping login'))
            
            server.quit()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ SMTP connection failed: {e}'))
            return
        
        # Try to send test email
        self.stdout.write(f"Sending test email to {email}...")
        try:
            result = send_mail(
                subject='Test Email from StatBox',
                message='This is a test email to verify your email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            if result:
                self.stdout.write(self.style.SUCCESS(f'✓ Test email sent successfully! Check {email} (and spam folder)'))
            else:
                self.stdout.write(self.style.WARNING('⚠ Email function returned False (may have failed silently)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to send email: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

