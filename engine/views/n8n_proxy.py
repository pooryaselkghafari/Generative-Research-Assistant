"""
Django view to proxy requests to n8n, ensuring admin authentication.
"""
import requests
from django.http import StreamingHttpResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
import logging
import urllib.parse

logger = logging.getLogger(__name__)

N8N_BASE_URL = 'http://127.0.0.1:5678'


@staff_member_required
def n8n_proxy(request, path=''):
    """
    Proxy requests to n8n, ensuring only admin users can access.
    
    This view handles all requests to /n8n/* and forwards them to n8n
    running on localhost:5678, preserving the request method, headers, and body.
    """
    try:
        # Build the target URL - remove leading slash from path if present
        path = path.lstrip('/') if path else ''
        if path:
            target_url = f"{N8N_BASE_URL}/{path}"
        else:
            target_url = N8N_BASE_URL
        
        # Add query string if present
        if request.GET:
            query_string = request.GET.urlencode()
            separator = '&' if '?' in target_url else '?'
            target_url = f"{target_url}{separator}{query_string}"
        
        # Prepare headers
        headers = {}
        
        # Copy relevant headers from request
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                # Skip cookies and authorization (we don't want to forward Django auth)
                if key in ['HTTP_COOKIE', 'HTTP_AUTHORIZATION']:
                    continue
                # Convert HTTP_HEADER_NAME to Header-Name
                header_name = key[5:].replace('_', '-').title()
                headers[header_name] = value
            elif key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
                headers[key.replace('_', '-')] = value
        
        # Set proper headers for n8n
        headers['Host'] = 'localhost:5678'
        headers['X-Forwarded-Proto'] = request.scheme
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Forwarded-For'] = request.META.get('REMOTE_ADDR', '')
        
        # Explicitly request uncompressed response OR let requests auto-decompress
        # Remove Accept-Encoding to get uncompressed, or keep it and let requests handle it
        # We'll keep Accept-Encoding but ensure requests decompresses
        
        # Get request body for methods that support it
        body = None
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            body = request.body
        
        logger.debug(f"Proxying {request.method} request to n8n: {target_url}")
        
        # Make request to n8n
        # Note: requests automatically decompresses gzip/deflate responses when stream=False
        # But we need to ensure the response is actually decompressed
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=body,
            stream=False,  # Set to False to let requests handle decompression automatically
            timeout=60,
            allow_redirects=False
        )
        
        # Force decompression if needed - requests should have done this automatically
        # But let's verify by checking if content-encoding is still present
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        if content_encoding in ['gzip', 'deflate', 'br']:
            # If still compressed, manually decompress
            import gzip
            if content_encoding == 'gzip':
                try:
                    response._content = gzip.decompress(response.content)
                except Exception as e:
                    logger.warning(f"Failed to decompress gzip content: {e}")
            # Remove content-encoding header
            del response.headers['Content-Encoding']
        
        # Prepare response headers
        response_headers = {}
        excluded_headers = ['transfer-encoding', 'connection', 'content-length']
        # We need to preserve content-encoding for gzip/deflate, but handle it properly
        for key, value in response.headers.items():
            key_lower = key.lower()
            if key_lower not in excluded_headers:
                response_headers[key] = value
        
        # Handle redirects - rewrite to use /n8n/ prefix
        if response.status_code in [301, 302, 303, 307, 308]:
            location = response.headers.get('Location', '')
            if location:
                if location.startswith('/'):
                    # Relative path - add /n8n prefix
                    location = f'/n8n{location}'
                elif location.startswith('http://localhost:5678/'):
                    # Absolute localhost URL - replace with /n8n/
                    location = location.replace('http://localhost:5678/', '/n8n/')
                elif location.startswith('http://127.0.0.1:5678/'):
                    # Absolute 127.0.0.1 URL - replace with /n8n/
                    location = location.replace('http://127.0.0.1:5678/', '/n8n/')
                response_headers['Location'] = location
        
        # requests library automatically decompresses gzip/deflate responses
        # So response.content is already decompressed
        # Remove content-encoding header since we've decompressed it
        response_headers.pop('Content-Encoding', None)
        response_headers.pop('content-encoding', None)
        
        # Create response with decompressed content
        django_response = HttpResponse(
            response.content,
            status=response.status_code
        )
        
        # Set content type
        content_type = response.headers.get('Content-Type', 'text/html')
        django_response['Content-Type'] = content_type
        
        # Set all other headers
        for key, value in response_headers.items():
            django_response[key] = value
        
        return django_response
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout proxying request to n8n: {e}", exc_info=True)
        return HttpResponse(
            "Timeout connecting to n8n. Please try again.",
            status=504,
            content_type='text/plain'
        )
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error proxying to n8n: {e}", exc_info=True)
        return HttpResponse(
            "Cannot connect to n8n. Please ensure n8n is running on port 5678.",
            status=502,
            content_type='text/plain'
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying request to n8n: {e}", exc_info=True)
        return HttpResponse(
            f"Error connecting to n8n: {str(e)}",
            status=502,
            content_type='text/plain'
        )
    except Exception as e:
        logger.error(f"Unexpected error in n8n proxy: {e}", exc_info=True)
        return HttpResponse(
            f"Unexpected error: {str(e)}",
            status=500,
            content_type='text/plain'
        )

