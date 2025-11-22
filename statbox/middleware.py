"""
Admin Security Middleware

Provides multiple layers of security for Django admin:
1. IP restriction
2. Token-based pre-authentication (double login)
3. Hide admin from unauthorized visitors (return 404)
"""
import logging
from django.http import Http404, HttpResponseForbidden
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AdminSecurityMiddleware(MiddlewareMixin):
    """
    Multi-layer security middleware for Django admin.
    
    Features:
    - IP restriction (whitelist only)
    - Token-based pre-authentication
    - Hide admin from unauthorized visitors (404 instead of 403)
    """
    
    def process_request(self, request):
        """Check admin access before processing request"""
        admin_url = getattr(settings, 'ADMIN_URL', 'gra-management')
        
        # Only apply to admin URLs
        if not request.path.startswith(f'/{admin_url}/'):
            return None
        
        # Get security settings
        admin_allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        admin_access_token = getattr(settings, 'ADMIN_ACCESS_TOKEN', None)
        admin_hide_from_unauthorized = getattr(settings, 'ADMIN_HIDE_FROM_UNAUTHORIZED', True)
        
        # Get client IP (handle proxies)
        client_ip = self._get_client_ip(request)
        
        # 1. IP Restriction Check
        if admin_allowed_ips:
            if client_ip not in admin_allowed_ips:
                logger.warning(f"Admin access denied: IP {client_ip} not in whitelist")
                if admin_hide_from_unauthorized:
                    raise Http404("Page not found")
                return HttpResponseForbidden("Access denied")
        
        # 2. Token-based Pre-authentication Check
        if admin_access_token:
            # Check for token in URL parameter, header, or cookie
            token_in_url = request.GET.get('token') == admin_access_token
            token_in_header = request.headers.get('X-Admin-Token') == admin_access_token
            token_in_cookie = request.COOKIES.get('admin_access_token') == admin_access_token
            
            if not (token_in_url or token_in_header or token_in_cookie):
                logger.warning(f"Admin access denied: Missing or invalid token from IP {client_ip}")
                if admin_hide_from_unauthorized:
                    raise Http404("Page not found")
                return HttpResponseForbidden("Access denied")
        
        # All checks passed
        return None
    
    def _get_client_ip(self, request):
        """Extract client IP address, handling proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain (original client)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

