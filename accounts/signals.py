"""
Signals to handle user profile creation for social accounts.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from engine.models import UserProfile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile when a new User is created (including via social auth).
    This is a fallback in case the adapter doesn't create the profile.
    """
    if created:
        try:
            profile, created_profile = UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'subscription_type': 'free',
                    'ai_tier': 'none'
                }
            )
            if created_profile:
                logger.info(f"Created UserProfile via signal for user: {instance.username}")
        except Exception as e:
            logger.error(f"Failed to create UserProfile via signal for user {instance.username}: {e}", exc_info=True)

