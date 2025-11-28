"""
Utility views.
"""
from django.http import FileResponse, Http404
from django.conf import settings
import os


def download_file(request, fname):
    path = os.path.join(settings.MEDIA_ROOT, fname)
    if not os.path.exists(path):
        raise Http404()
    return FileResponse(open(path, 'rb'))



