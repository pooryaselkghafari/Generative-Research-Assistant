"""
Admin view for embedded n8n interface.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.conf import settings


@staff_member_required
def n8n_embedded(request):
    """
    Render n8n in an embedded iframe within the admin dashboard.
    """
    # Get the admin URL prefix
    admin_url = getattr(settings, 'ADMIN_URL', 'whereadmingoeshere')
    
    # Build the n8n URL (relative to current domain)
    n8n_url = '/n8n/'
    
    context = {
        'n8n_url': n8n_url,
        'admin_url': admin_url,
    }
    
    return render(request, 'admin/n8n_embedded.html', context)

