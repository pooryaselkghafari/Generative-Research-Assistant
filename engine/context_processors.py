"""
Context processors for making site-wide data available to all templates.
"""
from .models import SiteSettings


def site_settings(request):
    """Make site settings (Google Analytics, etc.) available to all templates"""
    settings = SiteSettings.get_settings()
    return {
        'site_settings': settings,
    }

