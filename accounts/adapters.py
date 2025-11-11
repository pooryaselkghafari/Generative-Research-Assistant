"""
Custom adapters for django-allauth to handle user profile creation.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from engine.models import UserProfile
import logging

logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for regular signups."""
    
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)
        if commit:
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
        return user
    
    def send_account_already_exists_mail(self, email):
        """
        Override to prevent email sending errors from breaking social login.
        Fail silently if email sending fails.
        """
        try:
            super().send_account_already_exists_mail(email)
        except Exception as e:
            # Log the error but don't break the login flow
            logger.warning(f"Failed to send account already exists email to {email}: {str(e)}")
            # Don't re-raise - allow login to continue


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for OAuth signups."""
    
    def pre_social_login(self, request, sociallogin):
        """Called before social login completes."""
        pass
    
    def save_user(self, request, sociallogin, form=None):
        """Save user after social login."""
        user = super().save_user(request, sociallogin, form)
        # Create user profile for social accounts with free tier defaults
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'subscription_type': 'free',
                'ai_tier': 'none'
            }
        )
        
        # Update AI tier from tier settings if available (only for new profiles)
        if created:
            from engine.models import SubscriptionTierSettings
            try:
                tier_settings = SubscriptionTierSettings.objects.get(tier='free')
                profile.ai_tier = tier_settings.ai_tier
                profile.save()
            except SubscriptionTierSettings.DoesNotExist:
                pass
        
        return user
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social signups even if email already exists.
        This prevents the "account already exists" email from being sent.
        """
        return True

