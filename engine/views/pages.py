"""
Views for static pages, landing page, robots.txt, and sitemap.
"""
from django.shortcuts import render
from django.http import HttpResponse, Http404
from engine.models import Page, SubscriptionPlan, PrivacyPolicy, TermsOfService


def landing_view(request):
    """Landing page for Generative Research Assistant - shown to non-authenticated users
    Checks for dynamic landing page content from Page model first"""
    
    # Check if there's a custom landing page
    landing_page = Page.objects.filter(
        page_type='landing',
        is_default_landing=True,
        is_published=True
    ).first()
    
    if landing_page:
        # Process page content through template engine to render dynamic tags
        from django.template import engines
        
        # Load subscription plans for context
        plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly'))
        
        # Debug: Log plans count
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Landing page: Found {len(plans)} active subscription plans")
        for plan in plans:
            logger.info(f"  - {plan.name}: ${plan.price_monthly}/month")
        
        # ALWAYS process content through template engine to ensure dynamic updates
        # This ensures subscription plans update when changed in admin
        processed_content = landing_page.content
        try:
            # Use Django's template engine to properly render template tags
            django_engine = engines['django']
            
            # Ensure static and url template tags are loaded
            template_content = landing_page.content
            if '{% load static %}' not in template_content:
                template_content = '{% load static %}\n' + template_content
            
            # Wrap content in a template that loads subscription_tags if not already loaded
            # This ensures the template tag library is available
            if '{% load subscription_tags %}' not in template_content and 'subscription_plans' in template_content:
                # Add the load tag if subscription_plans is used but load tag is missing
                template_content = '{% load subscription_tags %}\n' + template_content
            
            template = django_engine.from_string(template_content)
            context = {
                'request': request,
                'plans': plans,  # Pass plans to template context for dynamic rendering
            }
            processed_content = template.render(context, request)
            logger.info(f"Successfully processed landing page template with {len(plans)} plans")
        except Exception as e:
            # If template rendering fails, use original content
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Failed to process template tags in landing page content: {e}\n{error_details}")
            print(f"Warning: Failed to process template tags in page content: {e}")
            print(error_details)
            processed_content = landing_page.content
        
        # Create a modified page object with processed content
        class ProcessedPage:
            def __init__(self, page, processed_content):
                # Copy all model fields
                for field in page._meta.get_fields():
                    if hasattr(page, field.name):
                        setattr(self, field.name, getattr(page, field.name))
                # Override content with processed version
                self.content = processed_content
                # Copy the model instance reference
                self._meta = page._meta
                self.pk = page.pk
        
        processed_page = ProcessedPage(landing_page, processed_content)
        
        # Render dynamic landing page
        return render(request, 'engine/page.html', {
            'page': processed_page,
            'is_landing': True,
            'plans': plans,  # Pass plans to template context
        })
    
    # Get active subscription plans for pricing section
    plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly'))
    
    # Debug: Print plans count
    print(f"DEBUG: Landing page - Found {len(plans)} active plans")
    for plan in plans:
        print(f"  - {plan.name}: features={plan.features}, ai_features={plan.ai_features}")
    
    # Fallback to default static landing page with dynamic plans
    return render(request, 'engine/landing.html', {
        'plans': plans
    })


def page_view(request, slug):
    """View for rendering dynamic pages"""
    try:
        page = Page.objects.get(slug=slug, is_published=True)
        return render(request, 'engine/page.html', {
            'page': page,
            'is_landing': False
        })
    except Page.DoesNotExist:
        raise Http404("Page not found")


def privacy_policy_view(request):
    """Display the current active privacy policy"""
    policy = PrivacyPolicy.objects.filter(is_active=True).order_by('-effective_date').first()
    
    if not policy:
        # Fallback to default content
        default_content = """
        <h1>Privacy Policy</h1>
        <p>Privacy policy content will be available here. Please contact the administrator.</p>
        """
        return render(request, 'engine/page.html', {
            'page': type('Page', (), {
                'title': 'Privacy Policy',
                'content': default_content,
                'meta_description': 'Privacy Policy for StatBox',
            })()
        })
    
    return render(request, 'engine/privacy_policy.html', {
        'policy': policy
    })


def terms_of_service_view(request):
    """Display the current active terms of service"""
    terms = TermsOfService.objects.filter(is_active=True).order_by('-effective_date').first()
    
    if not terms:
        # Fallback to default content
        default_content = """
        <h1>Terms of Service</h1>
        <p>Terms of service content will be available here. Please contact the administrator.</p>
        """
        return render(request, 'engine/page.html', {
            'page': type('Page', (), {
                'title': 'Terms of Service',
                'content': default_content,
                'meta_description': 'Terms of Service for StatBox',
            })()
        })
    
    return render(request, 'engine/terms_of_service.html', {
        'terms': terms
    })


def robots_txt(request):
    """Generate robots.txt dynamically based on pages"""
    # Get pages that don't allow indexing
    noindex_pages = Page.objects.filter(is_published=True, allow_indexing=False)
    
    lines = ['User-agent: *']
    
    # Add disallow rules for noindex pages
    if noindex_pages.exists():
        for page in noindex_pages:
            if page.page_type == 'landing' and page.is_default_landing:
                lines.append('Disallow: /')
            else:
                lines.append(f'Disallow: /page/{page.slug}/')
    
    lines.append('')  # Empty line
    lines.append('Allow: /')  # Allow everything else by default
    
    # Add sitemap reference
    lines.append('')
    lines.append('Sitemap: http://127.0.0.1:8000/sitemap.xml')
    
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def sitemap_xml(request):
    """Generate sitemap.xml dynamically based on published pages"""
    from django.utils import timezone
    from urllib.parse import urljoin
    
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    
    pages = Page.objects.filter(is_published=True, allow_indexing=True)
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    # Add homepage if there's a landing page
    landing_page = pages.filter(page_type='landing', is_default_landing=True).first()
    if landing_page:
        lastmod = landing_page.updated_at.strftime('%Y-%m-%d')
        xml_lines.extend([
            '  <url>',
            f'    <loc>{base_url}/</loc>',
            f'    <lastmod>{lastmod}</lastmod>',
            '    <changefreq>weekly</changefreq>',
            '    <priority>1.0</priority>',
            '  </url>'
        ])
    
    # Add other pages
    for page in pages.exclude(id=landing_page.id if landing_page else None):
        lastmod = page.updated_at.strftime('%Y-%m-%d')
        if page.page_type == 'landing':
            url_path = '/'
        else:
            url_path = f'/page/{page.slug}/'
        
        xml_lines.extend([
            '  <url>',
            f'    <loc>{base_url}{url_path}</loc>',
            f'    <lastmod>{lastmod}</lastmod>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.8</priority>',
            '  </url>'
        ])
    
    xml_lines.append('</urlset>')
    
    return HttpResponse('\n'.join(xml_lines), content_type='application/xml')


