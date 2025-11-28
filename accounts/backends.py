"""
Custom authentication backend that prevents inactive users from logging in.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class ActiveUserBackend(ModelBackend):
    """
    Authentication backend that only allows active users to authenticate.
    This enforces email verification requirement.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user, but only if they are active (email verified).
        """
        # First, try to get the user
        user = super().authenticate(request, username=username, password=password, **kwargs)
        
        # If user exists but is not active, return None (authentication fails)
        if user is not None and not user.is_active:
            return None
        
        return user



