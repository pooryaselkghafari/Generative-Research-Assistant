"""
Views for static pages, robots.txt, and sitemap.
"""
from django.shortcuts import render
from django.http import HttpResponse, Http404
from engine.models import Page, SubscriptionPlan, PrivacyPolicy, TermsOfService


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
        # Default content for open-source locally-run application
        default_content = """
        <h2>Privacy Policy</h2>
        <p><strong>Last Updated:</strong> December 2025</p>
        
        <h3>Overview</h3>
        <p>This application is an open-source tool designed to run locally on your machine. This privacy policy explains how your data is handled when you use this software.</p>
        
        <h3>Data Storage and Processing</h3>
        <p>All data processing and storage occurs locally on your machine:</p>
        <ul>
            <li><strong>Local Storage:</strong> All datasets, analysis results, and user data are stored locally on your computer. No data is transmitted to external servers unless you explicitly choose to do so.</li>
            <li><strong>No Cloud Services:</strong> This application does not use cloud storage or external data processing services by default.</li>
            <li><strong>No Tracking:</strong> The application does not include analytics, tracking scripts, or telemetry that would send data to third parties.</li>
        </ul>
        
        <h3>Data You Provide</h3>
        <p>When you use this application, you may upload datasets, create analysis sessions, and generate results. All of this data remains on your local machine:</p>
        <ul>
            <li>Uploaded datasets are stored in the local file system</li>
            <li>Analysis configurations and results are stored in a local database</li>
            <li>No personal information is collected or required for basic usage</li>
        </ul>
        
        <h3>Third-Party Services</h3>
        <p>This application is designed to operate independently without requiring third-party services. If you choose to integrate with external services (such as cloud storage or APIs), you are responsible for reviewing those services' privacy policies.</p>
        
        <h3>Open Source</h3>
        <p>As an open-source application, the source code is publicly available for review. You can inspect the code to verify how your data is handled.</p>
        
        <h3>Your Rights</h3>
        <p>Since all data is stored locally:</p>
        <ul>
            <li>You have full control over your data</li>
            <li>You can delete data at any time by removing files or using the application's delete functions</li>
            <li>You can export your data in standard formats</li>
            <li>No account or registration is required</li>
        </ul>
        
        <h3>Changes to This Policy</h3>
        <p>If this privacy policy is updated, the changes will be reflected in the source code repository. As the software runs locally, you control when and if you update to newer versions.</p>
        
        <h3>Contact</h3>
        <p>For questions about this privacy policy or the application, please refer to the project's source code repository or documentation.</p>
        """
        return render(request, 'engine/privacy_policy.html', {
            'policy': None,
            'default_content': default_content
        })
    
    return render(request, 'engine/privacy_policy.html', {
        'policy': policy
    })


def terms_of_service_view(request):
    """Display the current active terms of service"""
    terms = TermsOfService.objects.filter(is_active=True).order_by('-effective_date').first()
    
    if not terms:
        # Default content for open-source locally-run application
        default_content = """
        <h2>Terms of Use</h2>
        <p><strong>Last Updated:</strong> December 2025</p>
        
        <h3>Acceptance of Terms</h3>
        <p>By using this open-source application, you agree to be bound by these Terms of Use. If you do not agree to these terms, please do not use the application.</p>
        
        <h3>Open Source License</h3>
        <p>This software is provided as open-source software. Your use of this software is governed by the license terms specified in the source code repository. By using this software, you agree to comply with those license terms.</p>
        
        <h3>Local Installation and Use</h3>
        <p>This application is designed to run locally on your machine:</p>
        <ul>
            <li>You are responsible for installing and maintaining the software on your system</li>
            <li>You are responsible for ensuring your system meets the technical requirements</li>
            <li>You are responsible for backing up your data</li>
            <li>The software operates independently and does not require external services</li>
        </ul>
        
        <h3>No Warranty</h3>
        <p>This software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.</p>
        
        <h3>Data Responsibility</h3>
        <p>Since this application runs locally:</p>
        <ul>
            <li>You are solely responsible for the data you input and process</li>
            <li>You are responsible for ensuring compliance with applicable data protection laws</li>
            <li>You are responsible for maintaining appropriate security measures for your local installation</li>
            <li>The application does not transmit data externally unless you explicitly configure it to do so</li>
        </ul>
        
        <h3>Prohibited Uses</h3>
        <p>You agree not to use this application:</p>
        <ul>
            <li>For any unlawful purpose or to solicit others to perform unlawful acts</li>
            <li>To violate any international, federal, provincial, or state regulations, rules, laws, or local ordinances</li>
            <li>To infringe upon or violate our intellectual property rights or the intellectual property rights of others</li>
            <li>To harass, abuse, insult, harm, defame, slander, disparage, intimidate, or discriminate</li>
            <li>To submit false or misleading information</li>
        </ul>
        
        <h3>Modifications and Updates</h3>
        <p>As open-source software, this application may be modified by you or others. You are responsible for:</p>
        <ul>
            <li>Reviewing any modifications you make to the code</li>
            <li>Understanding the implications of any updates you install</li>
            <li>Maintaining compatibility with your data and workflows</li>
        </ul>
        
        <h3>Intellectual Property</h3>
        <p>The original code, documentation, and associated materials are subject to the license terms specified in the source code repository. You retain all rights to data you create using this application.</p>
        
        <h3>Termination</h3>
        <p>You may stop using this application at any time. Since the application runs locally, you can simply uninstall it or stop running it. Your data will remain on your local system unless you explicitly delete it.</p>
        
        <h3>Changes to Terms</h3>
        <p>These terms may be updated from time to time. Updated terms will be reflected in the source code repository. Your continued use of the application after such changes constitutes acceptance of the new terms.</p>
        
        <h3>Governing Law</h3>
        <p>These terms shall be governed by and construed in accordance with the laws applicable to the software license, without regard to its conflict of law provisions.</p>
        
        <h3>Contact</h3>
        <p>For questions about these terms, please refer to the project's source code repository or documentation.</p>
        """
        return render(request, 'engine/terms_of_service.html', {
            'terms': None,
            'default_content': default_content
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


