from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Use configurable admin URL for security (less predictable than /admin/)
admin_url = getattr(settings, 'ADMIN_URL', 'gra-management')
urlpatterns = [
    path(f'{admin_url}/', admin.site.urls),
    # Custom account URLs (login, register, etc.) - must come before allauth
    path('accounts/', include('accounts.urls')),
    # Allauth URLs for social auth (Google OAuth) - comes after custom URLs
    # Custom URLs take precedence, but allauth handles /accounts/google/login/ etc.
    path('accounts/', include('allauth.urls')),
    path('', include('engine.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add CKEditor URLs if installed
try:
    from ckeditor_uploader import urls as ckeditor_urls
    urlpatterns.insert(1, path('ckeditor/', include(ckeditor_urls)))
except ImportError:
    pass
