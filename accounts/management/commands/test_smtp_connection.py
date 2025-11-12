"""
Management command to test SMTP connection and diagnose firewall issues.
Usage: python manage.py test_smtp_connection
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import socket
import smtplib
import ssl


class Command(BaseCommand):
    help = 'Test SMTP connection and diagnose firewall/network issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Testing SMTP connectivity...'))
        self.stdout.write("")
        
        host = getattr(settings, 'EMAIL_HOST', 'smtp.resend.com')
        port = getattr(settings, 'EMAIL_PORT', 465)
        
        # Test 1: Basic TCP connection
        self.stdout.write(f"Test 1: Testing TCP connection to {host}:{port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                self.stdout.write(self.style.SUCCESS(f'✓ TCP connection to {host}:{port} successful'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ TCP connection to {host}:{port} failed (error code: {result})'))
                self.stdout.write(self.style.WARNING('This suggests a firewall or network issue'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ TCP connection failed: {e}'))
            self.stdout.write(self.style.WARNING('This suggests a firewall or network issue'))
            return
        
        # Test 2: DNS resolution
        self.stdout.write(f"\nTest 2: Testing DNS resolution for {host}...")
        try:
            ip = socket.gethostbyname(host)
            self.stdout.write(self.style.SUCCESS(f'✓ DNS resolution successful: {host} -> {ip}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ DNS resolution failed: {e}'))
            return
        
        # Test 3: SMTP SSL connection (port 465)
        if port == 465:
            self.stdout.write(f"\nTest 3: Testing SMTP SSL connection (port 465)...")
            try:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, timeout=10, context=context)
                self.stdout.write(self.style.SUCCESS('✓ SMTP SSL connection successful'))
                
                # Try to login
                if hasattr(settings, 'EMAIL_HOST_USER') and hasattr(settings, 'EMAIL_HOST_PASSWORD'):
                    try:
                        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                        self.stdout.write(self.style.SUCCESS('✓ SMTP authentication successful'))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'⚠ SMTP authentication failed: {e}'))
                        self.stdout.write(self.style.WARNING('This might be an API key issue, not a firewall issue'))
                
                server.quit()
            except socket.timeout:
                self.stdout.write(self.style.ERROR('✗ SMTP SSL connection timed out'))
                self.stdout.write(self.style.WARNING('This strongly suggests a firewall is blocking port 465'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ SMTP SSL connection failed: {e}'))
        
        # Test 4: Alternative port 587 (TLS)
        self.stdout.write(f"\nTest 4: Testing alternative port 587 (TLS)...")
        try:
            server = smtplib.SMTP(host, 587, timeout=10)
            server.starttls()
            self.stdout.write(self.style.SUCCESS('✓ SMTP TLS connection (port 587) successful'))
            server.quit()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Port 587 also failed: {e}'))
        
        # Test 5: Check if port is open using netcat (if available)
        self.stdout.write(f"\nTest 5: Checking firewall rules...")
        self.stdout.write("Run these commands on your server to check firewall:")
        self.stdout.write(f"  sudo ufw status | grep 465")
        self.stdout.write(f"  sudo iptables -L -n | grep 465")
        self.stdout.write(f"  telnet {host} {port}")
        self.stdout.write(f"  nc -zv {host} {port}")
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS('Diagnostic complete!'))

