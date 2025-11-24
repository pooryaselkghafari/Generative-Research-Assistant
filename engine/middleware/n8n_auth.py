"""
Middleware to protect n8n access - only allow authenticated admin users.
"""
import logging
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib.auth import logout

logger = logging.getLogger(__name__)


class N8nAuthMiddleware:
    """
    Middleware to check admin authentication before allowing access to /n8n/.
    
    This middleware runs before the request reaches n8n via the reverse proxy.
    It ensures only authenticated admin users can access the n8n GUI.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if request is for n8n
        if request.path.startswith('/n8n/'):
            # Allow access only if user is authenticated and is staff/admin
            # Use getattr with default to handle cases where user might not be set
            # Also check if user has is_authenticated attribute (it might not be set yet by AuthenticationMiddleware)
            user = getattr(request, 'user', None)
            is_authenticated = getattr(user, 'is_authenticated', False) if user else False
            if not user or not is_authenticated:
                logger.warning(
                    f"Unauthenticated access attempt to n8n: {request.path}",
                    extra={
                        'ip': request.META.get('REMOTE_ADDR'),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')
                    }
                )
                # Redirect to admin login
                admin_url = getattr(request, 'admin_url', '/whereadmingoeshere/login/')
                return redirect(f'{admin_url}?next={request.path}')
            
            if not user.is_staff:
                logger.warning(
                    f"Non-admin access attempt to n8n: {request.path}",
                    extra={
                        'user_id': user.id if user else None,
                        'username': user.username if user else 'anonymous',
                        'ip': request.META.get('REMOTE_ADDR')
                    }
                )
                return HttpResponseForbidden(
                    "Access denied. Only administrators can access n8n."
                )
            
            logger.info(
                f"Admin access to n8n: {request.path}",
                extra={
                    'user_id': user.id if user else None,
                    'username': user.username if user else 'anonymous'
                }
            )
        
        response = self.get_response(request)
        return response

