"""
Resend API email backend for Django.
Uses Resend's REST API instead of SMTP for better reliability.
"""
import json
import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ResendBackend(BaseEmailBackend):
    """
    Email backend that uses Resend's REST API.
    More reliable than SMTP, especially when SMTP ports are blocked.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'RESEND_API_KEY', None) or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.api_url = 'https://api.resend.com/emails'
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@generativera.com')
    
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of emails sent.
        """
        if not email_messages:
            return 0
        
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError('RESEND_API_KEY or EMAIL_HOST_PASSWORD must be set')
            return 0
        
        num_sent = 0
        for message in email_messages:
            try:
                # Prepare payload for Resend API
                payload = {
                    'from': message.from_email or self.from_email,
                    'to': message.to,
                    'subject': message.subject,
                }
                
                # Add CC and BCC if present
                if message.cc:
                    payload['cc'] = message.cc
                if message.bcc:
                    payload['bcc'] = message.bcc
                
                # Add reply-to if present
                if message.reply_to:
                    payload['reply_to'] = message.reply_to[0] if message.reply_to else None
                
                # Handle email content
                if hasattr(message, 'alternatives') and message.alternatives:
                    # HTML email with plain text alternative
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            payload['html'] = content
                        elif mimetype == 'text/plain':
                            payload['text'] = content
                    
                    # If no plain text alternative, use body
                    if 'text' not in payload:
                        payload['text'] = message.body
                else:
                    # Plain text email
                    payload['text'] = message.body
                
                # Send via Resend API
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                }
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    num_sent += 1
                    logger.info(f"Email sent successfully via Resend API to {message.to}")
                else:
                    error_msg = f"Resend API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    if not self.fail_silently:
                        raise Exception(error_msg)
            
            except Exception as e:
                logger.error(f"Failed to send email via Resend API: {e}")
                if not self.fail_silently:
                    raise
        
        return num_sent

