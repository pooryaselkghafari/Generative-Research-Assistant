"""
Signals to handle user profile creation for social accounts.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from engine.models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile when a new User is created (including via social auth).
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)

