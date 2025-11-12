"""
Email service for sending welcome, confirmation, and password reset emails.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse


def send_welcome_email(user):
    """
    Send a welcome email to a newly registered user.
    
    Args:
        user: User instance
    """
    try:
        subject = 'Welcome to StatBox!'
        html_message = render_to_string('accounts/emails/welcome.html', {
            'user': user,
            'site_name': 'StatBox',
            'login_url': settings.LOGIN_URL if hasattr(settings, 'LOGIN_URL') else '/accounts/login/',
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # Log email attempt
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to send welcome email to {user.email} from {from_email}")
        
        result = send_mail(
            subject,
            plain_message,
            from_email,
            [user.email],
            html_message=html_message,
            fail_silently=False,  # Set to False to see actual errors
        )
        # send_mail returns the number of emails sent (1 if successful, 0 if failed)
        if result > 0:
            logger.info(f"Welcome email sent successfully to {user.email}")
            return True
        else:
            logger.warning(f"Welcome email returned {result} (expected 1)")
            return False
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending welcome email to {user.email}: {e}\n{traceback.format_exc()}")
        print(f"Error sending welcome email: {e}")
        return False


def send_verification_email(user, request):
    """
    Send an email verification link to the user.
    
    Args:
        user: User instance
        request: HttpRequest object for building absolute URLs
    """
    try:
        # Generate token for email verification
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build verification URL
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )
        
        subject = 'Verify your StatBox email address'
        html_message = render_to_string('accounts/emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'StatBox',
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # Log email attempt
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to send verification email to {user.email} from {from_email}")
        
        result = send_mail(
            subject,
            plain_message,
            from_email,
            [user.email],
            html_message=html_message,
            fail_silently=False,  # Set to False to see actual errors
        )
        # send_mail returns the number of emails sent (1 if successful, 0 if failed)
        if result > 0:
            logger.info(f"Verification email sent successfully to {user.email}")
            return True
        else:
            logger.warning(f"Verification email returned {result} (expected 1)")
            return False
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending verification email to {user.email}: {e}\n{traceback.format_exc()}")
        print(f"Error sending verification email: {e}")
        return False


def send_password_reset_email(user, request):
    """
    Send a password reset link to the user.
    
    Args:
        user: User instance
        request: HttpRequest object for building absolute URLs
    """
    try:
        # Generate token for password reset
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build password reset URL
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
        subject = 'Reset your StatBox password'
        html_message = render_to_string('accounts/emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'StatBox',
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # Log email attempt
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to send password reset email to {user.email} from {from_email}")
        
        result = send_mail(
            subject,
            plain_message,
            from_email,
            [user.email],
            html_message=html_message,
            fail_silently=False,  # Set to False to see actual errors
        )
        # send_mail returns the number of emails sent (1 if successful, 0 if failed)
        if result > 0:
            logger.info(f"Password reset email sent successfully to {user.email}")
            return True
        else:
            logger.warning(f"Password reset email returned {result} (expected 1)")
            return False
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending password reset email to {user.email}: {e}\n{traceback.format_exc()}")
        print(f"Error sending password reset email: {e}")
        return False

