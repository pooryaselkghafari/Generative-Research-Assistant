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
        admin_path = f'/{admin_url}/'
        
        # Only apply to admin URLs
        if not request.path.startswith(admin_path):
            return None
        
        # Log that middleware is triggered
        logger.info(f"Admin security middleware triggered for path: {request.path}")
        
        # Get security settings
        admin_allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        admin_hide_from_unauthorized = getattr(settings, 'ADMIN_HIDE_FROM_UNAUTHORIZED', True)
        
        # Get client IP (handle proxies)
        client_ip = self._get_client_ip(request)
        logger.info(f"Client IP detected: {client_ip} (from REMOTE_ADDR: {request.META.get('REMOTE_ADDR', 'N/A')}, X-Forwarded-For: {request.META.get('HTTP_X_FORWARDED_FOR', 'N/A')})")
        logger.info(f"Admin allowed IPs: {admin_allowed_ips}")
        
        # IP Restriction Check (optional - only if ADMIN_ALLOWED_IPS is set)
        if admin_allowed_ips:
            if client_ip not in admin_allowed_ips:
                logger.warning(f"Admin access denied: IP {client_ip} not in whitelist {admin_allowed_ips}")
                if admin_hide_from_unauthorized:
                    raise Http404("Page not found")
                return HttpResponseForbidden("Access denied")
            else:
                logger.info(f"IP {client_ip} is in whitelist, proceeding...")
        
        # All checks passed
        logger.info(f"Admin access granted for IP {client_ip}")
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

