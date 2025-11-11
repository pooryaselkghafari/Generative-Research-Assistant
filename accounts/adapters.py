"""
Custom adapters for django-allauth to handle user profile creation.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from engine.models import UserProfile


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for regular signups."""
    
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)
        if commit:
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for OAuth signups."""
    
    def pre_social_login(self, request, sociallogin):
        """Called before social login completes."""
        pass
    
    def save_user(self, request, sociallogin, form=None):
        """Save user after social login."""
        user = super().save_user(request, sociallogin, form)
        # Create user profile for social accounts
        UserProfile.objects.get_or_create(user=user)
        return user

