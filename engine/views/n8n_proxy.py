"""
Django view to proxy requests to n8n, ensuring admin authentication.
"""
import requests
from django.http import StreamingHttpResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

N8N_BASE_URL = 'http://127.0.0.1:5678'


@staff_member_required
@require_http_methods(["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def n8n_proxy(request, path=''):
    """
    Proxy requests to n8n, ensuring only admin users can access.
    
    This view handles all requests to /n8n/* and forwards them to n8n
    running on localhost:5678, preserving the request method, headers, and body.
    """
    # Build the target URL
    if path:
        target_url = f"{N8N_BASE_URL}/{path}"
    else:
        target_url = N8N_BASE_URL
    
    # Add query string if present
    if request.GET:
        query_string = request.GET.urlencode()
        target_url = f"{target_url}?{query_string}"
    
    # Prepare headers (exclude Django-specific headers)
    headers = {}
    for key, value in request.META.items():
        if key.startswith('HTTP_') and key not in ['HTTP_HOST', 'HTTP_COOKIE', 'HTTP_AUTHORIZATION']:
            # Convert HTTP_HEADER_NAME to Header-Name
            header_name = key[5:].replace('_', '-').title()
            headers[header_name] = value
        elif key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
            headers[key.replace('_', '-')] = value
    
    # Set proper host
    headers['Host'] = 'localhost:5678'
    headers['X-Forwarded-Proto'] = request.scheme
    headers['X-Forwarded-Host'] = request.get_host()
    
    # Get request body for POST/PUT/PATCH
    body = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        body = request.body
    
    try:
        # Make request to n8n
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=body,
            stream=True,
            timeout=60,
            allow_redirects=False
        )
        
        # Prepare response headers (exclude n8n-specific headers we don't want to forward)
        response_headers = {}
        excluded_headers = ['content-encoding', 'transfer-encoding', 'connection']
        for key, value in response.headers.items():
            if key.lower() not in excluded_headers:
                response_headers[key] = value
        
        # Handle redirects
        if response.status_code in [301, 302, 303, 307, 308]:
            # Rewrite redirect location to use /n8n/ prefix
            location = response.headers.get('Location', '')
            if location.startswith('/'):
                location = f'/n8n{location}'
            elif location.startswith('http://localhost:5678/'):
                location = location.replace('http://localhost:5678/', '/n8n/')
            response_headers['Location'] = location
        
        # Create streaming response
        django_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'text/html')
        )
        
        # Set headers
        for key, value in response_headers.items():
            django_response[key] = value
        
        return django_response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying request to n8n: {e}", exc_info=True)
        return HttpResponse(
            f"Error connecting to n8n: {str(e)}",
            status=502,
            content_type='text/plain'
        )

