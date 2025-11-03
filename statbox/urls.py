from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('engine.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add CKEditor URLs if installed
try:
    from ckeditor_uploader import urls as ckeditor_urls
    urlpatterns.insert(1, path('ckeditor/', include(ckeditor_urls)))
except ImportError:
    pass
