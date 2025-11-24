"""
Django view to proxy requests to n8n, ensuring admin authentication.
"""
import requests
from django.http import StreamingHttpResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
import logging
import urllib.parse
import re

logger = logging.getLogger(__name__)

# n8n base URL - use localhost since we're in the same Docker network (host mode)
N8N_BASE_URL = 'http://127.0.0.1:5678'


@csrf_exempt
@staff_member_required
def n8n_proxy(request, path=None):
    """
    Proxy requests to n8n, ensuring only admin users can access.
    
    This view handles all requests to /n8n/* and forwards them to n8n
    running on localhost:5678, preserving the request method, headers, and body.
    """
    try:
        logger.info(f"n8n_proxy called: path={path}, request.path={request.path}, method={request.method}")
        
        # Build the target URL - remove leading slash from path if present
        # Handle both cases: path parameter provided or not
        if path is None:
            # Extract path from request.path (remove /n8n/ prefix)
            request_path = request.path
            if request_path.startswith('/n8n/'):
                path = request_path[5:]  # Remove '/n8n/' prefix
            else:
                path = ''
        
        path = path.lstrip('/') if path else ''
        if path:
            target_url = f"{N8N_BASE_URL}/{path}"
        else:
            # For root /n8n/, target n8n root
            target_url = f"{N8N_BASE_URL}/"
        
        logger.info(f"Target URL: {target_url}")
        
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
        # Remove X-Forwarded-For header entirely
        headers.pop('X-Forwarded-For', None)
        
        # Remove Accept-Encoding to request uncompressed response from n8n
        # This avoids compression issues in the proxy chain
        if 'Accept-Encoding' in headers:
            del headers['Accept-Encoding']
        
        # Get request body for methods that support it
        body = None
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            body = request.body
        
        logger.info(f"Proxying {request.method} request to n8n: {target_url} (path: {path})")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Body: {body[:200] if body else None}")
        
        # Make request to n8n
        # We've removed Accept-Encoding, so n8n should return uncompressed content
        try:
            response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=body,
            stream=False,
            timeout=60,
            allow_redirects=False
            )
            logger.info(f"Received response from n8n: {response.status_code} for {target_url}")
        except Exception as request_error:
            # Log the error before re-raising so outer handler can catch it
            logger.error(f"Error making request to n8n at {target_url}: {request_error}", exc_info=True)
            raise
        
        # Check if response is actually compressed
        # Sometimes Content-Encoding header is set but content isn't actually compressed
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        if content_encoding in ['gzip', 'deflate']:
            # Check if content is actually compressed by looking at magic bytes
            # Only check if we have at least 2 bytes
            if len(response.content) >= 2:
                content_bytes = response.content[:2]
                is_gzipped = content_bytes == b'\x1f\x8b'  # gzip magic bytes
                
                if is_gzipped and content_encoding == 'gzip':
                    # Content is actually gzipped, decompress it
                    import gzip
                    try:
                        response._content = gzip.decompress(response.content)
                        # Remove content-encoding header after decompression
                        if 'Content-Encoding' in response.headers:
                            del response.headers['Content-Encoding']
                        logger.debug(f"Decompressed gzip content from n8n")
                    except Exception as e:
                        logger.warning(f"Failed to decompress gzip content: {e}")
                        # Remove the header even if decompression failed
                        if 'Content-Encoding' in response.headers:
                            del response.headers['Content-Encoding']
                else:
                    # Header says gzip but content isn't actually compressed - remove the header
                    if 'Content-Encoding' in response.headers:
                        del response.headers['Content-Encoding']
                    logger.debug(f"Content-Encoding header present but content is not compressed, removing header")
            else:
                # Content too short to be gzipped, remove header
                if 'Content-Encoding' in response.headers:
                    del response.headers['Content-Encoding']
                logger.debug(f"Content too short to be compressed, removing Content-Encoding header")
        
        # Prepare response headers (handle multi-value headers like Set-Cookie separately)
        response_headers = {}
        excluded_headers = ['transfer-encoding', 'connection', 'content-length', 'set-cookie']
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
        
        # Get content type
        content_type = response.headers.get('Content-Type', 'text/html')
        
        # For HTML/JavaScript content, rewrite URLs to use /n8n/ prefix
        # But be smart: n8n with N8N_PATH already generates /n8n/ URLs, so don't double-prefix
        content = response.content
        if content_type.startswith('text/html') or content_type.startswith('application/javascript') or content_type.startswith('text/javascript'):
            try:
                content_str = content.decode('utf-8')
                # Only rewrite URLs that don't already start with /n8n/
                # Use regex to be more precise
                import re
                
                # n8n with N8N_PATH=/n8n/ already generates URLs with /n8n/ prefix
                # So we need to be careful not to double-prefix
                # Only rewrite URLs that don't already start with /n8n/
                
                # Replace href="/..." but not href="/n8n/..." (avoid double prefix)
                content_str = re.sub(r'href="/(?!n8n/)', 'href="/n8n/', content_str)
                content_str = re.sub(r"href='/(?!n8n/)", "href='/n8n/", content_str)
                
                # Replace src="/..." but not src="/n8n/..." (avoid double prefix)
                content_str = re.sub(r'src="/(?!n8n/)', 'src="/n8n/', content_str)
                content_str = re.sub(r"src='/(?!n8n/)", "src='/n8n/", content_str)
                
                # Replace action="/..." but not action="/n8n/..." (avoid double prefix)
                content_str = re.sub(r'action="/(?!n8n/)', 'action="/n8n/', content_str)
                content_str = re.sub(r"action='/(?!n8n/)", "action='/n8n/", content_str)
                
                # Replace API calls that don't have /n8n/ prefix (avoid double prefix)
                content_str = re.sub(r'"/rest/(?!n8n/)', '"/n8n/rest/', content_str)
                content_str = re.sub(r"'/rest/(?!n8n/)", "'/n8n/rest/", content_str)
                content_str = re.sub(r'"/webhook/(?!n8n/)', '"/n8n/webhook/', content_str)
                content_str = re.sub(r"'/webhook/(?!n8n/)", "'/n8n/webhook/", content_str)
                
                # Replace base URLs (these should always be replaced)
                content_str = content_str.replace('http://localhost:5678/', '/n8n/')
                content_str = content_str.replace('http://127.0.0.1:5678/', '/n8n/')
                
                # Fix any double prefixes that might have been created
                content_str = content_str.replace('/n8n/n8n/', '/n8n/')
                
                content = content_str.encode('utf-8')
            except (UnicodeDecodeError, AttributeError) as e:
                # If content can't be decoded as text, use as-is
                logger.debug(f"Could not decode content for URL rewriting: {e}")
                pass
        
        # Create response with content
        django_response = HttpResponse(
            content,
            status=response.status_code
        )
        
        # Set content type
        django_response['Content-Type'] = content_type

        # Copy Set-Cookie headers explicitly (requests collapses duplicates)
        set_cookie_headers = []
        raw_headers = getattr(response.raw, 'headers', None)
        if raw_headers is not None:
            try:
                set_cookie_headers = raw_headers.getlist('Set-Cookie')
            except Exception:
                set_cookie_headers = []
        if not set_cookie_headers:
            cookie_header = response.headers.get('Set-Cookie')
            if cookie_header:
                set_cookie_headers = [cookie_header]
        for cookie in set_cookie_headers:
            try:
                django_response.headers.appendlist('Set-Cookie', cookie)
            except AttributeError:
                # Fallback for older Django versions
                if 'Set-Cookie' in django_response:
                    django_response['Set-Cookie'] += f'\n{cookie}'
                else:
                    django_response['Set-Cookie'] = cookie
        
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

