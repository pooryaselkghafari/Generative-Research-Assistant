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
            # Create user profile with free plan defaults
            try:
                from engine.models import SubscriptionPlan
                free_plan, _ = SubscriptionPlan.objects.get_or_create(
                    name='Free',
                    defaults={
                        'description': 'Free tier with basic features',
                        'price_monthly': 0,
                        'price_yearly': 0,
                        'max_datasets': 5,
                        'max_sessions': 10,
                        'max_file_size_mb': 10,
                        'is_active': True,
                    }
                )
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'subscription_plan': free_plan
                    }
                )
                if created and not profile.subscription_plan:
                    profile.subscription_plan = free_plan
                    profile.save()
            except Exception as e:
                # Log error but don't break registration
                logger.error(f"Failed to create user profile in adapter: {e}")
                # Profile can be created later via signals
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
        
        # Create user profile for social accounts with free plan defaults
        # This is critical for Google OAuth users
        try:
            from engine.models import SubscriptionPlan
            free_plan, _ = SubscriptionPlan.objects.get_or_create(
                name='Free',
                defaults={
                    'description': 'Free tier with basic features',
                    'price_monthly': 0,
                    'price_yearly': 0,
                    'max_datasets': 5,
                    'max_sessions': 10,
                    'max_file_size_mb': 10,
                    'ai_tier': 'none',
                    'is_active': True,
                }
            )
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'subscription_plan': free_plan
                }
            )
            if created and not profile.subscription_plan:
                profile.subscription_plan = free_plan
                profile.save()
            
            if created:
                logger.info(f"Created UserProfile for Google OAuth user: {user.username}")
            else:
                logger.info(f"UserProfile already exists for user: {user.username}")
                
        except Exception as e:
            # Log error but don't break login - profile can be created later
            logger.error(f"Failed to create UserProfile for Google OAuth user {user.username}: {e}", exc_info=True)
            # Try to create a basic profile as fallback
            try:
                from engine.models import SubscriptionPlan
                free_plan = SubscriptionPlan.objects.filter(name='Free').first()
                if free_plan:
                    UserProfile.objects.create(
                        user=user,
                        subscription_plan=free_plan
                    )
                    logger.info(f"Created fallback UserProfile for user: {user.username}")
            except Exception as e2:
                logger.error(f"Failed to create fallback UserProfile for user {user.username}: {e2}", exc_info=True)
        
        return user
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social signups even if email already exists.
        This prevents the "account already exists" email from being sent.
        """
        return True

