import os
import uuid
import json
import pandas as pd
import numpy as np
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Dataset, AnalysisSession
from .modules import get_registry, get_module
from data_prep.file_handling import _read_dataset_file, _apply_types
from data_prep.cleaning import add_statistical_functions
from models.regression import generate_spotlight_for_interaction, _build_correlation_heatmap_json, _get_continuous_variables, _get_continuous_variables_from_formula
from history.history import download_session_history, track_session_iteration

os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
DATASET_DIR = os.path.join(settings.MEDIA_ROOT, 'datasets')
os.makedirs(DATASET_DIR, exist_ok=True)

def landing_view(request):
    """Landing page for Generative Research Assistant - shown to non-authenticated users
    Checks for dynamic landing page content from Page model first"""
    from .models import Page, SubscriptionPlan
    
    # Check if there's a custom landing page
    landing_page = Page.objects.filter(
        page_type='landing',
        is_default_landing=True,
        is_published=True
    ).first()
    
    if landing_page:
        # Process page content through template engine to render dynamic tags
        from django.template import Context, Template
        from django.template.loader import get_template
        from django.template import engines
        
        # Load subscription plans for context
        plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly'))
        
        # ALWAYS process content through template engine to ensure dynamic updates
        # This ensures subscription plans update when changed in admin
        processed_content = landing_page.content
        try:
            # Use Django's template engine to properly render template tags
            from django.template import engines
            django_engine = engines['django']
            
            # Wrap content in a template that loads subscription_tags if not already loaded
            # This ensures the template tag library is available
            template_content = landing_page.content
            if '{% load subscription_tags %}' not in template_content and 'subscription_plans' in template_content:
                # Add the load tag if subscription_plans is used but load tag is missing
                template_content = '{% load subscription_tags %}\n' + template_content
            
            template = django_engine.from_string(template_content)
            context = {
                'request': request,
                'plans': plans,
            }
            processed_content = template.render(context, request)
        except Exception as e:
            # If template rendering fails, use original content
            import traceback
            print(f"Warning: Failed to process template tags in page content: {e}")
            print(traceback.format_exc())
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
    from .models import Page
    
    try:
        page = Page.objects.get(slug=slug, is_published=True)
        return render(request, 'engine/page.html', {
            'page': page,
            'is_landing': False
        })
    except Page.DoesNotExist:
        from django.http import Http404
        raise Http404("Page not found")

def privacy_policy_view(request):
    """Display the current active privacy policy"""
    from .models import PrivacyPolicy
    
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
    from .models import TermsOfService
    
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
    from .models import Page
    from django.http import HttpResponse
    
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
    from .models import Page
    from django.http import HttpResponse
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

def _list_context(current_session=None):
    sessions = AnalysisSession.objects.order_by('-updated_at')[:50]
    datasets = Dataset.objects.order_by('-uploaded_at')
    registry = get_registry()
    return {
        'sessions': sessions,
        'datasets': datasets,
        'modules': registry,
        'current': current_session,
        'line_styles': ['solid', 'dashed', 'dotted', 'dashdot'],
    }

def index(request):
    # Redirect non-authenticated users to landing page
    if not request.user.is_authenticated:
        return redirect('landing')
    
    # Check if a specific session should be loaded
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = get_object_or_404(AnalysisSession, pk=session_id)
            context = _list_context(current_session=session)
        except (ValueError, AnalysisSession.DoesNotExist):
            # Invalid session_id, just use default context
            context = _list_context()
    else:
        context = _list_context()
    
    # Check if a specific dataset should be auto-selected
    dataset_id = request.GET.get('dataset_id')
    if dataset_id:
        context['auto_select_dataset_id'] = dataset_id
    
    return render(request, 'engine/index.html', context)

def edit_session(request, pk: int):
    s = get_object_or_404(AnalysisSession, pk=pk)
    return render(request, 'engine/index.html', _list_context(current_session=s))


def get_dataset_variables(request, dataset_id):
    """API endpoint to get variables from a dataset"""
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        # Use efficient column-only loading for large datasets
        from engine.dataprep.loader import get_dataset_columns_only
        variables, column_types = get_dataset_columns_only(dataset.file_path)
        return JsonResponse({
            'success': True,
            'variables': variables,
            'column_types': column_types,
            'dataset_name': dataset.name
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def update_sessions_for_variable_rename(request, dataset_id):
    """API endpoint to update all sessions when variables are renamed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST only'})
    
    try:
        # Get the rename mapping from request
        import json
        rename_map = json.loads(request.POST.get('rename_map', '{}'))
        
        if not rename_map:
            return JsonResponse({'success': False, 'error': 'No rename mapping provided'})
        
        # Find all sessions using this dataset
        sessions = AnalysisSession.objects.filter(dataset_id=dataset_id)
        updated_count = 0
        
        for session in sessions:
            # Update the formula with new variable names
            old_formula = session.formula
            new_formula = old_formula
            
            # Replace each old variable name with new name
            for old_name, new_name in rename_map.items():
                if old_name != new_name:  # Only replace if actually changed
                    # Use word boundaries to avoid partial matches
                    import re
                    pattern = r'\b' + re.escape(old_name) + r'\b'
                    new_formula = re.sub(pattern, new_name, new_formula)
            
            # Only update if formula actually changed
            if new_formula != old_formula:
                session.formula = new_formula
                session.save()
                updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_sessions': updated_count,
            'message': f'Updated {updated_count} analysis sessions'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def upload_dataset(request):
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    if 'dataset' not in request.FILES:
        return HttpResponse('No dataset file provided', status=400)
    
    # Check user authentication and limits
    user = request.user if request.user.is_authenticated else None
    if user:
        profile = user.profile
        limits = profile.get_limits()
        
        # Check dataset count limit
        if limits['datasets'] != -1:  # -1 means unlimited
            current_count = user.datasets.count()
            if current_count >= limits['datasets']:
                error_msg = f"You have reached your dataset limit ({limits['datasets']} datasets). Please delete some datasets or upgrade your plan."
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=403)
                from django.contrib import messages
                messages.error(request, error_msg)
                return redirect('index')
        
        # Check file size limit
        file_size_mb = request.FILES['dataset'].size / (1024 * 1024)
        if limits['file_size'] != -1 and file_size_mb > limits['file_size']:
            error_msg = f"File size ({file_size_mb:.2f} MB) exceeds your plan limit ({limits['file_size']} MB). Please upgrade your plan."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=403)
            from django.contrib import messages
            messages.error(request, error_msg)
            return redirect('index')
    
    name = request.POST.get('dataset_name') or request.FILES['dataset'].name
    f = request.FILES['dataset']
    safe = f.name.replace(' ', '_')
    slug = str(uuid.uuid4())[:8]
    path = os.path.join(DATASET_DIR, f"{slug}_{safe}")
    
    # Calculate file size in MB
    file_size_mb = f.size / (1024 * 1024)
    
    with open(path, 'wb') as dest:
        for chunk in f.chunks():
            dest.write(chunk)
    
    # Use get_or_create with user to handle unique_together constraint
    if user:
        dataset, created = Dataset.objects.get_or_create(
            name=name,
            user=user,
            defaults={
                'file_path': path,
                'file_size_mb': file_size_mb
            }
        )
        if not created:
            # Update existing dataset
            dataset.file_path = path
            dataset.file_size_mb = file_size_mb
            dataset.save()
    else:
        # No user - update or create without user constraint
        dataset, created = Dataset.objects.update_or_create(
            name=name,
            user=None,
            defaults={
                'file_path': path,
                'file_size_mb': file_size_mb
            }
        )
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'message': 'Dataset uploaded successfully'
        })
    
    # If this is a new dataset, redirect with the dataset ID to auto-select it
    if created:
        return redirect(f'/app/?dataset_id={dataset.id}')
    return redirect('index')

def delete_dataset(request, pk: int):
    ds = get_object_or_404(Dataset, pk=pk)
    # Detach sessions from this dataset
    AnalysisSession.objects.filter(dataset=ds).update(dataset=None)
    try:
        if os.path.exists(ds.file_path):
            os.remove(ds.file_path)
    except Exception:
        pass
    ds.delete()
    return redirect('index')

def run_analysis(request):
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    action = request.POST.get('action', 'new')  # 'new' or 'update'
    session_id = request.POST.get('session_id')
    print(f"DEBUG: run_analysis - action: {action}, session_id: {session_id}")
    print(f"DEBUG: run_analysis - POST data: {dict(request.POST)}")

    dataset_id = request.POST.get('dataset_id')
    if not dataset_id:
        return HttpResponse('Please select a dataset from the dropdown', status=400)
    dataset = get_object_or_404(Dataset, pk=dataset_id)

    try:
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Check if dataset is very large and warn user
        if len(df) > 100000:  # More than 100k rows
            # For very large datasets, suggest sampling
            sample_size = min(50000, len(df))  # Sample up to 50k rows
            if request.POST.get('use_sample', 'false').lower() == 'true':
                df = df.sample(n=sample_size, random_state=42)
                print(f"Using sample of {sample_size} rows from dataset with {len(df)} total rows")
            else:
                # Return a warning response suggesting to use sampling
                return JsonResponse({
                    'success': False,
                    'error': f'Dataset is very large ({len(df):,} rows). This may cause performance issues.',
                    'suggestion': 'Consider using a sample of the data for analysis.',
                    'sample_size': sample_size,
                    'total_rows': len(df)
                })
    except Exception as e:
        return HttpResponse(f'Failed to read dataset: {e}', status=400)

    analysis_type = request.POST.get('analysis_type', 'frequentist')
    template_override = request.POST.get('template_override', '')
    
    # Force module selection based on analysis type
    if analysis_type == 'bayesian':
        module_name = 'bayesian'
        print(f"DEBUG: Analysis type is Bayesian, forcing module_name to 'bayesian'")
    else:
        module_name = request.POST.get('module', 'regression')
        print(f"DEBUG: Analysis type is {analysis_type}, using module_name: {module_name}")
    formula = request.POST.get('formula', '')

    options = {
        # Display options
        'show_se': request.POST.get('show_se') == 'on',
        'show_ci': request.POST.get('show_ci') == 'on',
        'bootstrap': request.POST.get('bootstrap', 'off') == 'on',
        'n_boot': int(request.POST.get('n_boot', '500')),
        'interaction_terms': request.POST.get('interaction_terms', ''),
        'x_name': request.POST.get('x_name') or None,
        'y_name': request.POST.get('y_name') or None,
        'moderator_name': request.POST.get('moderator_name') or None,
        'plot_color_low': request.POST.get('plot_color_low', '#999999'),
        'plot_color_high': request.POST.get('plot_color_high', '#111111'),
        'line_style_low': request.POST.get('line_style_low', 'solid'),
        'line_style_high': request.POST.get('line_style_high', 'dashed'),
        'spotlight_ci': request.POST.get('spotlight_ci', 'on') == 'on',
        'partial_covariates': request.POST.get('partial_covariates', '').strip(),
        'custom_labels': request.POST.get('custom_labels', '').strip(),
        'show_t': request.POST.get('show_t') == 'on',
        'show_p': request.POST.get('show_p') == 'on',
        'show_min': request.POST.get('show_min', 'on') == 'on',  # Default to True
        'show_max': request.POST.get('show_max', 'on') == 'on',  # Default to True
        'show_range': request.POST.get('show_range') == 'on',
        'show_variance': request.POST.get('show_variance') == 'on',
        'show_vif': request.POST.get('show_vif') == 'on',
        'show_r2': request.POST.get('show_r2') == 'on',
        'show_aic': request.POST.get('show_aic') == 'on',
        
        # Bayesian model parameters
        'draws': int(request.POST.get('draws', '2000')),
        'tune': int(request.POST.get('tune', '1000')),
        'chains': int(request.POST.get('chains', '4')),
        'cores': int(request.POST.get('cores', '2')),
        'prior': request.POST.get('prior', 'auto'),
    }

    # Detect if dependent variable is ordered categorical to inform module selection
    try:
        dep_var = (formula.split('~', 1)[0] or '').strip()
        if dep_var in df.columns:
            col = df[dep_var]
            is_ordered = hasattr(col.dtype, 'ordered') and bool(getattr(col.dtype, 'ordered'))
            options['dependent_is_ordered'] = is_ordered
        else:
            options['dependent_is_ordered'] = False
    except Exception:
        options['dependent_is_ordered'] = False

    # Note: show_r2 is now handled by the user's explicit checkbox choice
    # No automatic enabling to avoid interfering with user preferences

    session_name = request.POST.get('session_name') or f"Session {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Check session limits for new sessions (not updates)
    if action == 'new' and request.user.is_authenticated:
        profile = request.user.profile
        limits = profile.get_limits()
        
        # Check session count limit
        if limits['sessions'] != -1:  # -1 means unlimited
            current_count = request.user.sessions.count()
            if current_count >= limits['sessions']:
                error_msg = f"You have reached your session limit ({limits['sessions']} sessions). Please delete some sessions or upgrade your plan."
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=403)
                from django.contrib import messages
                messages.error(request, error_msg)
                return redirect('index')

    # Special handling for BMA analysis
    if module_name == 'bma':
        # Redirect to BMA analysis
        return run_bma_analysis(request)
    
    # Special handling for ANOVA analysis
    if module_name == 'anova':
        # Redirect to ANOVA analysis
        return run_anova_analysis(request)
    
    # Special handling for VARX analysis
    if module_name == 'varx':
        # Redirect to VARX analysis
        return run_varx_analysis(request)
    
    job_id = str(uuid.uuid4())[:8]
    outdir = os.path.join(settings.MEDIA_ROOT, job_id)
    os.makedirs(outdir, exist_ok=True)

    mod = get_module(module_name)
    results = mod.run(df, formula=formula, analysis_type=analysis_type, outdir=outdir, options=options, schema_types=column_types, schema_orders=schema_orders)
    # --- Build table data for the template (robust to old/new module return formats) ---
    def _stars(p):
        try:
            p = float(p)
        except Exception:
            return ""
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        if p < 0.10:  return "."
        return ""

    cols = results.get("model_table_cols", [])
    rows = results.get("model_table_rows", [])

    # Fallback ONLY if the new keys are missing (old module shape)
    if (not cols) and isinstance(results.get("model_table"), dict):
        old = results["model_table"]
        if "columns" in old and "data" in old:
            cols = ["Term", "Estimate"]
            rows = []
            oc = old["columns"]; od = old["data"]
            term_idx = oc.index("term") if "term" in oc else None
            coef_idx = oc.index("coef") if "coef" in oc else None
            p_idx    = oc.index("p")    if "p" in oc else None
            stat_idx = oc.index("stat") if "stat" in oc else None
            def _stars(p):
                try: p = float(p)
                except Exception: return ""
                return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "." if p < 0.10 else ""
            for r in od:
                term = r[term_idx] if term_idx is not None else ""
                coef = r[coef_idx] if coef_idx is not None else ""
                pval = r[p_idx]    if p_idx is not None else None
                stat = r[stat_idx] if stat_idx is not None else ""
                cell = f"{coef}{_stars(pval)}<div class='sub'>{stat}</div>"
                rows.append({"Term": term, "Estimate": cell})

    # Build matrix for template
    if cols and rows:
        # Handle both list of lists (Bayesian) and list of dicts (other modules)
        if rows and isinstance(rows[0], list):
            # Bayesian format: list of lists
            model_table_matrix = rows
        else:
            # Other modules format: list of dicts
            model_table_matrix = [[row.get(c, "") for c in cols] for row in rows]
        estimate_col_index = cols.index("Estimate") if "Estimate" in cols else -1
    else:
        model_table_matrix, estimate_col_index = [], -1
    # --- end table prep ---
    
    if action == 'update' and session_id:
        print(f"DEBUG: Updating existing session {session_id}")
        sess = get_object_or_404(AnalysisSession, pk=session_id)
        
        
        sess.name = session_name
        sess.module = module_name
        sess.formula = formula
        sess.analysis_type = analysis_type
        sess.options = options
        sess.dataset = dataset
        # Ensure user is set if not already set
        if not sess.user and request.user.is_authenticated:
            sess.user = request.user
    else:
        print(f"DEBUG: Creating new session (action: {action}, session_id: {session_id})")
        # Associate session with user if authenticated
        user = request.user if request.user.is_authenticated else None
        sess = AnalysisSession(
            name=session_name, module=module_name, formula=formula,
            analysis_type=analysis_type, options=options, dataset=dataset,
            user=user
        )

    sess.spotlight_rel = results.get('spotlight_rel')
    
    # Store the fitted model for future spotlight plot generation
    fitted_model = results.get('fitted_model')
    if fitted_model:
        try:
            import pickle
            sess.fitted_model = pickle.dumps(fitted_model)
            print("Stored fitted model in session")
        except Exception as e:
            print(f"Failed to store fitted model: {e}")
    
    # Store ordinal predictions if available
    ordinal_predictions = results.get('ordinal_predictions')
    if ordinal_predictions:
        try:
            sess.ordinal_predictions = ordinal_predictions
            print("Stored ordinal predictions in session")
        except Exception as e:
            print(f"Failed to store ordinal predictions: {e}")
    
    # Store multinomial predictions if available
    multinomial_predictions = results.get('multinomial_predictions')
    print(f"DEBUG: multinomial_predictions from results: {multinomial_predictions}")
    if multinomial_predictions:
        try:
            sess.multinomial_predictions = multinomial_predictions
            print("Stored multinomial predictions in session")
        except Exception as e:
            print(f"Failed to store multinomial predictions: {e}")
    else:
        print("DEBUG: No multinomial predictions to store")
    
    sess.save()

    # Track this analysis iteration in session history
    try:
        iteration_type = 'update' if action == 'update' and session_id else 'initial'
        plots_added = []  # Will be populated when plots are added
        
        # Prepare results data with table information
        results_with_tables = results.copy()
        results_with_tables['model_cols'] = cols
        results_with_tables['model_matrix'] = model_table_matrix
        
        track_session_iteration(
            session_id=sess.id,
            iteration_type=iteration_type,
            equation=formula,
            analysis_type=analysis_type,
            results_data=results_with_tables,
            plots_added=plots_added,
            modifications={
                'module': module_name,
                'options': {k: v for k, v in options.items() if k not in ['draws', 'tune', 'chains', 'cores', 'prior']}
            },
            notes=f"Analysis completed successfully with {module_name} module"
        )
    except Exception as e:
        print(f"Failed to track session history: {e}")

    # Get dataset columns for help text
    try:
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        dataset_columns = list(df.columns)
        print(f"DEBUG: Dataset columns after update: {dataset_columns}")
        print(f"DEBUG: Summary stats keys: {list(results.get('summary_stats', {}).keys())}")
        print(f"DEBUG: Continuous vars: {results.get('continuous_vars', [])}")
        
        # Extract DV categories for ordinal regression
        dv_categories = []
        if 'Ordinal regression' in results.get('regression_type', ''):
            # Parse formula to get dependent variable
            formula = sess.formula
            if '~' in formula:
                dv = formula.split('~')[0].strip()
                if dv in df.columns:
                    dv_categories = sorted(df[dv].dropna().unique().tolist())
                    print(f"DEBUG: DV categories for ordinal regression: {dv_categories}")
        
        # Extract DV categories for multinomial regression
        multinomial_categories = []
        if 'Multinomial regression' in results.get('regression_type', ''):
            # Parse formula to get dependent variable
            formula = sess.formula
            if '~' in formula:
                dv = formula.split('~')[0].strip()
                if dv in df.columns:
                    multinomial_categories = sorted(df[dv].dropna().unique().tolist())
                    print(f"DEBUG: DV categories for multinomial regression: {multinomial_categories}")
    except Exception:
        dataset_columns = []
        dv_categories = []
        multinomial_categories = []
    
    import json
    
    print(f"DEBUG: regression_type from results: {results.get('regression_type', 'Not found')}")
    
    # DEBUG: Print template condition values
    print(f"DEBUG VIEWS: model_cols = {cols}")
    print(f"DEBUG VIEWS: model_matrix = {model_table_matrix}")
    print(f"DEBUG VIEWS: model_cols truthy = {bool(cols)}")
    print(f"DEBUG VIEWS: model_matrix truthy = {bool(model_table_matrix)}")
    print(f"DEBUG VIEWS: condition result = {bool(cols) and bool(model_table_matrix)}")
    
    ctx = {
    'session': sess,
    'dataset': dataset,
    'dataset_columns': dataset_columns,
    'dataset_columns_json': json.dumps(dataset_columns),
    **results,
    'model_cols': cols,
    'model_matrix': model_table_matrix,
    'estimate_col_index': estimate_col_index,
    'show_min': options.get('show_min', True),  # Default to True
    'show_max': options.get('show_max', True),  # Default to True
    'show_range': options.get('show_range', False),
    'show_variance': options.get('show_variance', False),
    'show_vif': options.get('show_vif', False),
    'summary_stats': results.get('summary_stats'),
    'summary_stats_json': json.dumps(results.get('summary_stats', {})),
    'interactions': results.get('interactions', []),
    'dv_categories': dv_categories,
    'dv_categories_json': json.dumps(dv_categories),
    'multinomial_categories': multinomial_categories,
    'multinomial_categories_json': json.dumps(multinomial_categories),
    'continuous_vars': results.get('continuous_vars', []),
    'continuous_vars_json': json.dumps(results.get('continuous_vars', [])),
    'all_numeric_vars': results.get('all_numeric_vars', []),
    'all_numeric_vars_json': json.dumps(results.get('all_numeric_vars', [])),
    }
    
    # Use template override if provided, otherwise use analysis_type
    if template_override:
        template_name = f'engine/{template_override}.html'
        print(f"DEBUG: Using template override: {template_name}")
    elif analysis_type == 'bayesian':
        template_name = 'engine/bayesian_results.html'
        print(f"DEBUG: Rendering bayesian_results.html for analysis_type: {analysis_type}")
    else:
        template_name = 'engine/results.html'
        print(f"DEBUG: Rendering results.html for analysis_type: {analysis_type}")
    
    return render(request, template_name, ctx)

def visualize_data(request):
    """Handle visualization requests"""
    if request.method == 'POST':
        # Handle plot generation requests
        if request.POST.get('action') == 'generate_plot':
            return generate_plot(request)
        
        # Handle initial page load with dataset
        dataset_id = request.POST.get('dataset_id')
        if not dataset_id:
            return HttpResponse('Please select a dataset from the dropdown', status=400)
        
        try:
            dataset = get_object_or_404(Dataset, pk=dataset_id)
            df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
            
            # Get column information
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            # Treat object/category and low-cardinality numeric/boolean columns as categorical for grouping
            categorical_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
            # Add low-cardinality numeric columns (e.g., 0/1 or small enums) as groupable
            try:
                max_categories = 20
                row_count = len(df)
                threshold = max_categories if row_count > 0 else max_categories
                for col in numeric_columns:
                    if col not in categorical_columns:
                        unique_count = int(df[col].nunique(dropna=True))
                        if unique_count <= threshold:
                            categorical_columns.append(col)
            except Exception:
                # If anything goes wrong during detection, fall back to existing list
                pass
            # Preserve the original column order
            all_columns = df.columns.tolist()
            categorical_columns = [c for c in all_columns if c in set(categorical_columns)]
            
            context = {
                'dataset': dataset,
                'numeric_columns': numeric_columns,
                'categorical_columns': categorical_columns,
                'all_columns': all_columns,
                'numeric_columns_json': json.dumps(numeric_columns),
                'categorical_columns_json': json.dumps(categorical_columns),
                'all_columns_json': json.dumps(all_columns),
            }
            
            return render(request, 'engine/visualize.html', context)
            
        except Exception as e:
            return HttpResponse(f'Error loading dataset: {e}', status=400)
    
    return HttpResponse('Method not allowed', status=405)

def generate_plot(request):
    """Generate a plot based on user selections"""
    try:
        dataset_id = request.POST.get('dataset_id')
        plot_type = request.POST.get('plot_type')
        
        if not dataset_id or not plot_type:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Import visualization functions
        from models.visualization import (
            generate_scatter_plot, generate_histogram, generate_bar_chart,
            generate_line_chart, generate_pie_chart
        )
        
        # Get plot parameters
        x_var = request.POST.get('x_var')
        y_var = request.POST.get('y_var')
        group_var = request.POST.get('group_var') or None
        trendline = request.POST.get('trendline') == 'true'
        bins = int(request.POST.get('bins', 30))
        
        # Get custom styling options from request
        x_label = request.POST.get('x_label', '')
        y_label = request.POST.get('y_label', '')
        point_color = request.POST.get('point_color', '')
        bar_color = request.POST.get('bar_color', '')
        line_color = request.POST.get('line_color', '')
        line_style = request.POST.get('line_style', '')
        background_color = request.POST.get('background_color', '')
        color_scheme = request.POST.get('color_scheme', '')
        
        # Prepare custom styling kwargs
        style_kwargs = {}
        if x_label: style_kwargs['x_label'] = x_label
        if y_label: style_kwargs['y_label'] = y_label
        if point_color: style_kwargs['point_color'] = point_color
        if bar_color: style_kwargs['bar_color'] = bar_color
        if line_color: style_kwargs['line_color'] = line_color
        if line_style: style_kwargs['line_style'] = line_style
        if background_color: style_kwargs['background_color'] = background_color
        if color_scheme: style_kwargs['color_scheme'] = color_scheme
        
        # Generate the appropriate plot
        if plot_type == 'scatter':
            if not x_var or not y_var:
                return JsonResponse({'error': 'X and Y variables required for scatter plot'}, status=400)
            fig = generate_scatter_plot(df, x_var, y_var, group_var, trendline, **style_kwargs)
            
        elif plot_type == 'histogram':
            if not x_var:
                return JsonResponse({'error': 'Variable required for histogram'}, status=400)
            fig = generate_histogram(df, x_var, group_var, bins, **style_kwargs)
            
        elif plot_type == 'bar':
            if not x_var:
                return JsonResponse({'error': 'X variable required for bar chart'}, status=400)
            fig = generate_bar_chart(df, x_var, y_var, group_var, **style_kwargs)
            
        elif plot_type == 'line':
            if not x_var or not y_var:
                return JsonResponse({'error': 'X and Y variables required for line chart'}, status=400)
            fig = generate_line_chart(df, x_var, y_var, group_var, **style_kwargs)
            
        elif plot_type == 'pie':
            if not x_var:
                return JsonResponse({'error': 'Variable required for pie chart'}, status=400)
            fig = generate_pie_chart(df, x_var, group_var, **style_kwargs)
            
        else:
            return JsonResponse({'error': 'Invalid plot type'}, status=400)
        
        # Convert plot to JSON
        plot_json = fig.to_json()
        
        return JsonResponse({
            'success': True,
            'plot_data': plot_json,
            'plot_type': plot_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def calculate_summary_stats(request, session_id):
    """Calculate summary statistics for selected variables."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        session = AnalysisSession.objects.get(id=session_id)
        dataset = session.dataset
        
        # Get selected variables from request
        selected_vars = request.POST.getlist('variables[]')
        if not selected_vars:
            return JsonResponse({'error': 'No variables selected'}, status=400)
        
        # Load dataset
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Calculate summary statistics for selected variables
        summary_stats = {}
        for var in selected_vars:
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
                series = df[var].dropna()
                if len(series) > 0:
                    summary_stats[var] = {
                        'min': float(series.min()),
                        'max': float(series.max()),
                        'range': float(series.max() - series.min()),
                        'variance': float(series.var(ddof=1)),
                        'vif': float('nan')  # VIF not calculated for non-formula variables
                    }
        
        return JsonResponse({'summary_stats': summary_stats})
        
    except AnalysisSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

import os
import shutil
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from .models import AnalysisSession

def delete_session(request, pk: int):
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    s = get_object_or_404(AnalysisSession, pk=pk)

    # Best-effort cleanup of this session’s output folder(s) under MEDIA_ROOT
    rels = [s.spotlight_rel]
    outdirs = set()
    for r in rels:
        if r:
            # r looks like "abcd1234/spotlight.jpg" → we remove MEDIA_ROOT/abcd1234
            first = os.path.normpath(r).split(os.sep)[0]
            if first and first not in ('.', '..'):
                outdirs.add(first)

    for d in outdirs:
        absdir = os.path.join(settings.MEDIA_ROOT, d)
        try:
            if os.path.isdir(absdir):
                shutil.rmtree(absdir)
        except Exception:
            # Ignore any filesystem errors; deletion of the DB row still proceeds
            pass

    s.delete()
    return redirect('index')


def bulk_delete_sessions(request):
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    session_ids = request.POST.getlist('session_ids')
    if not session_ids:
        return redirect('index')
    
    # Get sessions to delete
    sessions_to_delete = AnalysisSession.objects.filter(id__in=session_ids)
    deleted_count = 0
    
    # Delete each session (with cleanup)
    for session in sessions_to_delete:
        # Best-effort cleanup of this session's output folder(s) under MEDIA_ROOT
        rels = [session.spotlight_rel]
        outdirs = set()
        for r in rels:
            if r:
                # r looks like "abcd1234/spotlight.jpg" → we remove MEDIA_ROOT/abcd1234
                first = os.path.normpath(r).split(os.sep)[0]
                if first and first not in ('.', '..'):
                    outdirs.add(first)

        for d in outdirs:
            absdir = os.path.join(settings.MEDIA_ROOT, d)
            try:
                if os.path.isdir(absdir):
                    shutil.rmtree(absdir)
            except Exception:
                # Ignore any filesystem errors; deletion of the DB row still proceeds
                pass
        
        session.delete()
        deleted_count += 1
    
    return redirect('index')


def preview_drop_rows(request, dataset_id):
    """API endpoint to preview which rows would be dropped"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        data = json.loads(request.body)
        conditions = data.get('conditions', [])
        
        if not conditions:
            return JsonResponse({'error': 'No conditions provided'}, status=400)
        
        # Apply conditions to find rows to drop
        rows_to_drop = pd.Series([False] * len(df))  # Start with no rows to drop
        
        for condition in conditions:
            operator = condition.get('operator', 'drop')
            formula = condition.get('formula', '')
            
            if not formula:
                continue
                
            try:
                # Validate the formula before evaluation
                if not formula.strip():
                    return JsonResponse({'error': 'Empty condition provided'}, status=400)
                
                # Check for common syntax errors
                if '=' in formula and '==' not in formula and '!=' not in formula and '>=' not in formula and '<=' not in formula:
                    return JsonResponse({'error': f'Use == for equality comparison, not =. Did you mean: {formula.replace("=", "==")}'}, status=400)
                
                # Convert AND/OR/NOT to lowercase (pandas eval requires lowercase)
                import re
                formula = re.sub(r'\bAND\b', 'and', formula)
                formula = re.sub(r'\bOR\b', 'or', formula)
                formula = re.sub(r'\bNOT\b', 'not', formula)
                
                # Add support for statistical functions
                formula_with_functions = add_statistical_functions(df, formula)
                
                # Evaluate the condition
                condition_result = df.eval(formula_with_functions)
                
                if operator == 'drop':
                    # Drop rows where condition is True
                    rows_to_drop = rows_to_drop | condition_result
                else:  # keep
                    # Keep rows where condition is True, so drop rows where condition is False
                    rows_to_drop = rows_to_drop | ~condition_result
                    
            except Exception as e:
                error_msg = str(e)
                # Provide more helpful error messages
                if "unsupported operand type(s)" in error_msg:
                    return JsonResponse({'error': 'Invalid data types in condition. Make sure you are comparing compatible types (e.g., numbers with numbers, strings with strings)'}, status=400)
                elif "name" in error_msg and "is not defined" in error_msg:
                    return JsonResponse({'error': f'Column name not found. Available columns: {list(df.columns)}'}, status=400)
                elif "invalid syntax" in error_msg.lower():
                    return JsonResponse({'error': f'Invalid syntax in condition. Please check your operators (==, !=, >, <, >=, <=, and, or). Note: Use lowercase "and"/"or", not "AND"/"OR".'}, status=400)
                else:
                    return JsonResponse({'error': f'Invalid condition: {error_msg}'}, status=400)
        
        # Get rows that will be dropped
        rows_to_drop_df = df[rows_to_drop]
        rows_to_keep = df[~rows_to_drop]
        
        # Get preview of first 10 rows to be dropped
        preview_rows = rows_to_drop_df.head(10).to_dict('records')
        
        return JsonResponse({
            'success': True,
            'rows_to_drop': len(rows_to_drop_df),
            'rows_remaining': len(rows_to_keep),
            'columns': list(df.columns),
            'preview_rows': preview_rows
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def apply_drop_rows(request, dataset_id):
    """API endpoint to apply row dropping"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        data = json.loads(request.body)
        conditions = data.get('conditions', [])
        
        if not conditions:
            return JsonResponse({'error': 'No conditions provided'}, status=400)
        
        # Apply conditions to find rows to drop
        rows_to_drop = pd.Series([False] * len(df))  # Start with no rows to drop
        
        for condition in conditions:
            operator = condition.get('operator', 'drop')
            formula = condition.get('formula', '')
            
            if not formula:
                continue
                
            try:
                # Validate the formula before evaluation
                if not formula.strip():
                    return JsonResponse({'error': 'Empty condition provided'}, status=400)
                
                # Check for common syntax errors
                if '=' in formula and '==' not in formula and '!=' not in formula and '>=' not in formula and '<=' not in formula:
                    return JsonResponse({'error': f'Use == for equality comparison, not =. Did you mean: {formula.replace("=", "==")}'}, status=400)
                
                # Convert AND/OR/NOT to lowercase (pandas eval requires lowercase)
                import re
                formula = re.sub(r'\bAND\b', 'and', formula)
                formula = re.sub(r'\bOR\b', 'or', formula)
                formula = re.sub(r'\bNOT\b', 'not', formula)
                
                # Add support for statistical functions
                formula_with_functions = add_statistical_functions(df, formula)
                
                # Evaluate the condition
                condition_result = df.eval(formula_with_functions)
                
                if operator == 'drop':
                    # Drop rows where condition is True
                    rows_to_drop = rows_to_drop | condition_result
                else:  # keep
                    # Keep rows where condition is True, so drop rows where condition is False
                    rows_to_drop = rows_to_drop | ~condition_result
                    
            except Exception as e:
                error_msg = str(e)
                # Provide more helpful error messages
                if "unsupported operand type(s)" in error_msg:
                    return JsonResponse({'error': 'Invalid data types in condition. Make sure you are comparing compatible types (e.g., numbers with numbers, strings with strings)'}, status=400)
                elif "name" in error_msg and "is not defined" in error_msg:
                    return JsonResponse({'error': f'Column name not found. Available columns: {list(df.columns)}'}, status=400)
                elif "invalid syntax" in error_msg.lower():
                    return JsonResponse({'error': f'Invalid syntax in condition. Please check your operators (==, !=, >, <, >=, <=, and, or). Note: Use lowercase "and"/"or", not "AND"/"OR".'}, status=400)
                else:
                    return JsonResponse({'error': f'Invalid condition: {error_msg}'}, status=400)
        
        # Apply the mask to keep only the rows we want
        df_filtered = df[~rows_to_drop]
        
        # Save the filtered dataset back to the file
        file_extension = dataset.file_path.lower().split('.')[-1]
        if file_extension in ['xlsx', 'xls']:
            df_filtered.to_excel(dataset.file_path, index=False)
        else:  # CSV
            df_filtered.to_csv(dataset.file_path, index=False)
        
        rows_dropped = len(df) - len(df_filtered)
        
        return JsonResponse({
            'success': True,
            'rows_dropped': rows_dropped,
            'rows_remaining': len(df_filtered)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def download_file(request, fname):
    path = os.path.join(settings.MEDIA_ROOT, fname)
    if not os.path.exists(path):
        raise Http404()
    return FileResponse(open(path, 'rb'))


def _generate_multinomial_ordinal_spotlight_from_predictions(predictions, interaction, category, options):
    """Generate spotlight plot from pre-generated ordinal or multinomial predictions."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
        
        # Parse interaction to get variable names
        if "*" in interaction:
            parts = [p.strip() for p in interaction.split("*")]
            if len(parts) >= 2:
                x, m = parts[0], parts[1]
            else:
                return None
        else:
            parts = interaction.split(":")
            if len(parts) >= 2:
                x, m = parts[0].strip(), parts[1].strip()
            else:
                return None
        
        # Get moderator levels (should be exactly 2: low and high)
        moderator_levels = list(predictions.keys())
        print(f"DEBUG: Available moderator levels: {moderator_levels}")
        if len(moderator_levels) < 2:
            print(f"DEBUG: Not enough moderator levels: {len(moderator_levels)}")
            return None
            
        # Sort levels to ensure consistent low/high ordering
        numeric_levels = []
        for level in moderator_levels:
            try:
                numeric_levels.append(float(level))
            except ValueError:
                continue
        
        if numeric_levels:
            numeric_levels.sort()
            low_level = str(numeric_levels[0])
            high_level = str(numeric_levels[1])
        else:
            # Use first two available levels
            low_level = moderator_levels[0]
            high_level = moderator_levels[1]
        
        print(f"DEBUG: Selected low_level: {low_level}, high_level: {high_level}")
        print(f"DEBUG: Available categories in low_level: {list(predictions[low_level].keys()) if low_level in predictions else 'Not found'}")
        print(f"DEBUG: Available categories in high_level: {list(predictions[high_level].keys()) if high_level in predictions else 'Not found'}")
        print(f"DEBUG: Looking for category: {category}")
        
        if (low_level not in predictions or high_level not in predictions or 
            category not in predictions[low_level] or 
            category not in predictions[high_level]):
            print(f"DEBUG: Missing data - low_level in predictions: {low_level in predictions}")
            print(f"DEBUG: Missing data - high_level in predictions: {high_level in predictions}")
            if low_level in predictions:
                print(f"DEBUG: Missing data - category in low_level: {category in predictions[low_level]}")
            if high_level in predictions:
                print(f"DEBUG: Missing data - category in high_level: {category in predictions[high_level]}")
            return None
            
        # Get data for both levels
        low_data = predictions[low_level][category]
        high_data = predictions[high_level][category]
        x_values = low_data['x_values']
        low_probs = low_data['probabilities']
        high_probs = high_data['probabilities']
        
        # Create the plot
        fig = go.Figure()
        
        # Get custom names and styles
        x_label = options.get('x_name', x)
        y_label = options.get('y_name', f'Probability of {category}')
        
        # Handle moderator name - use custom name if provided, otherwise use the actual moderator variable
        moderator_var = options.get('moderator_var')
        if moderator_var and moderator_var.strip():
            moderator_name = moderator_var.strip()
        else:
            moderator_name = m
        
        legend_low = options.get('legend_low', f'Low {moderator_name}')
        legend_high = options.get('legend_high', f'High {moderator_name}')
        
        # Get line styles
        line_style_low = options.get('line_style_low', 'solid')
        line_style_high = options.get('line_style_high', 'dashed')
        
        # Convert line style to Plotly format
        def get_plotly_dash(style):
            style_map = {
                'solid': None,
                'dashed': 'dash',
                'dotted': 'dot',
                'dashdot': 'dashdot'
            }
            return style_map.get(style, None)
        
        # Add low moderator line
        fig.add_trace(go.Scatter(
            x=x_values,
            y=low_probs,
            mode='lines',
            name=legend_low,
            line=dict(
                color=options.get('color_low', '#1f77b4'),
                width=2,
                dash=get_plotly_dash(line_style_low)
            )
        ))
        
        # Add high moderator line
        fig.add_trace(go.Scatter(
            x=x_values,
            y=high_probs,
            mode='lines',
            name=legend_high,
            line=dict(
                color=options.get('color_high', '#ff7f0e'),
                width=2,
                dash=get_plotly_dash(line_style_high)
            )
        ))
        
        # Update layout
        fig.update_layout(
            title=f'Probability of {category} by {x_label} (Low vs High {moderator_name})',
            xaxis_title=x_label,
            yaxis_title=y_label,
            showlegend=True,
            plot_bgcolor=options.get('background_color', 'white'),
            paper_bgcolor='white'
        )
        
        # Add grid if requested
        if options.get('show_grid', True):
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        # Convert to JSON
        return pio.to_json(fig)
        
    except Exception as e:
        print(f"Error generating ordinal spotlight from predictions: {e}")
        return None

def generate_spotlight_plot(request, session_id):
    """Generate spotlight plot for a specific interaction."""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    session = get_object_or_404(AnalysisSession, pk=session_id)
    interaction = request.POST.get('interaction')
    
    if not interaction:
        return HttpResponse('Interaction required', status=400)
    
    try:
        # Load the dataset
        df, schema_types, schema_orders = _read_dataset_file(session.dataset.file_path)
        print(f"Dataset columns: {list(df.columns)}")
        print(f"Requested interaction: {interaction}")
        print(f"Custom moderator: {request.POST.get('moderator_var', 'None')}")
        
        # Check if we have a stored fitted model in the session
        fitted_model = None
        if hasattr(session, 'fitted_model') and session.fitted_model:
            # Try to load the fitted model from the stored data
            try:
                import pickle
                fitted_model = pickle.loads(session.fitted_model)
                print("Using stored fitted model")
            except Exception as e:
                print(f"Failed to load stored model: {e}")
                fitted_model = None
        
        # If no stored model, run the analysis to get the fitted model
        if not fitted_model:
            print("No stored model found, running analysis...")
            module = get_module(session.module)
            results = module.run(df, session.formula, session.analysis_type, settings.MEDIA_ROOT, session.options)
            fitted_model = results.get('fitted_model')
            
            # Store the fitted model in the session for future use
            if fitted_model:
                try:
                    import pickle
                    session.fitted_model = pickle.dumps(fitted_model)
                    session.save()
                    print("Stored fitted model in session")
                except Exception as e:
                    print(f"Failed to store model: {e}")
        
        if not fitted_model:
            return HttpResponse('No fitted model available', status=500)
        
        # Create custom options for spotlight plot
        custom_options = session.options.copy()
        
        # Override with custom values from the form
        if request.POST.get('moderator_var'):
            custom_options['moderator_var'] = request.POST.get('moderator_var')
            print(f"Custom moderator: {custom_options['moderator_var']}")
        if request.POST.get('x_name'):
            custom_options['x_name'] = request.POST.get('x_name')
        if request.POST.get('y_name'):
            custom_options['y_name'] = request.POST.get('y_name')
        if request.POST.get('legend_low'):
            custom_options['legend_low'] = request.POST.get('legend_low')
        if request.POST.get('legend_high'):
            custom_options['legend_high'] = request.POST.get('legend_high')
        if request.POST.get('color_low'):
            custom_options['color_low'] = request.POST.get('color_low')
        if request.POST.get('color_high'):
            custom_options['color_high'] = request.POST.get('color_high')
        if request.POST.get('line_style_low'):
            custom_options['line_style_low'] = request.POST.get('line_style_low')
        if request.POST.get('line_style_high'):
            custom_options['line_style_high'] = request.POST.get('line_style_high')
        if request.POST.get('show_ci'):
            custom_options['show_ci'] = request.POST.get('show_ci') == 'true'
        if request.POST.get('show_grid'):
            custom_options['show_grid'] = request.POST.get('show_grid') == 'true'
        if request.POST.get('background_color'):
            custom_options['background_color'] = request.POST.get('background_color')
        if request.POST.get('moderator_separation'):
            custom_options['moderator_separation'] = request.POST.get('moderator_separation')
        if request.POST.get('moderator_std_dev_multiplier'):
            custom_options['moderator_std_dev_multiplier'] = request.POST.get('moderator_std_dev_multiplier')
            print(f"Custom moderator_std_dev_multiplier: {custom_options['moderator_std_dev_multiplier']}")
        if request.POST.get('ordinal_category'):
            custom_options['ordinal_category'] = request.POST.get('ordinal_category')
        if request.POST.get('multinomial_category'):
            custom_options['multinomial_category'] = request.POST.get('multinomial_category')
            print(f"Custom multinomial_category: {custom_options['multinomial_category']}")
        
        print(f"Custom options: {custom_options}")
        
        # Check if this is an ordinal regression model
        is_ordinal = 'Ordinal regression' in str(type(fitted_model)) or hasattr(fitted_model, 'model') and 'OrderedModel' in str(type(fitted_model.model))
        
        # Check if this is a multinomial regression model - use same logic as ordinal
        is_multinomial = 'Multinomial regression' in str(type(fitted_model)) or hasattr(fitted_model, 'model') and 'mnlogit' in str(type(fitted_model.model))
        print(f"DEBUG: is_multinomial = {is_multinomial}")
        print(f"DEBUG: fitted_model type = {type(fitted_model)}")
        print(f"DEBUG: fitted_model str = {str(type(fitted_model))}")
        
        # Check if the session has the appropriate predictions based on regression type
        if is_ordinal:
            print(f"DEBUG: session has ordinal_predictions: {hasattr(session, 'ordinal_predictions')}")
            if hasattr(session, 'ordinal_predictions'):
                print(f"DEBUG: ordinal_predictions value: {session.ordinal_predictions}")
        elif is_multinomial:
            print(f"DEBUG: session has multinomial_predictions: {hasattr(session, 'multinomial_predictions')}")
            if hasattr(session, 'multinomial_predictions'):
                print(f"DEBUG: multinomial_predictions value: {session.multinomial_predictions}")
        
        # For ordinal regression, try to use pre-generated predictions
        if is_ordinal and hasattr(session, 'ordinal_predictions') and session.ordinal_predictions:
            ordinal_category = custom_options.get('ordinal_category')
            if ordinal_category and interaction in session.ordinal_predictions:
                # Check if we need to use a different separation method or std dev multiplier
                separation_method = custom_options.get('moderator_separation', 'mean')
                std_dev_multiplier_raw = custom_options.get('moderator_std_dev_multiplier', 1.0)
                try:
                    std_dev_multiplier = float(std_dev_multiplier_raw)
                except (ValueError, TypeError):
                    std_dev_multiplier = 1.0
                    print(f"DEBUG: Could not convert std_dev_multiplier '{std_dev_multiplier_raw}' to float, using 1.0")
                
                # Only use pre-generated predictions if using default settings (mean + 1.0 std dev)
                print(f"DEBUG: Ordinal regression - separation_method: {separation_method}, std_dev_multiplier: {std_dev_multiplier}")
                if separation_method == 'mean' and std_dev_multiplier == 1.0:
                    print(f"DEBUG: Using pre-generated ordinal predictions")
                    # Use pre-generated predictions for fast plotting (std_dev method)
                    ordinal_options = custom_options.copy()
                    
                    # Parse interaction to get variable names for proper labeling
                    if "*" in interaction:
                        parts = [p.strip() for p in interaction.split("*")]
                        if len(parts) >= 2:
                            x_var, moderator_var = parts[0], parts[1]
                        else:
                            x_var, moderator_var = interaction, "Moderator"
                    else:
                        parts = interaction.split(":")
                        if len(parts) >= 2:
                            x_var, moderator_var = parts[0].strip(), parts[1].strip()
                        else:
                            x_var, moderator_var = interaction, "Moderator"
                    
                    # Set default variable names if not provided
                    if not ordinal_options.get('x_name'):
                        ordinal_options['x_name'] = x_var
                    if not ordinal_options.get('moderator_var'):
                        ordinal_options['moderator_var'] = moderator_var
                    if not ordinal_options.get('y_name'):
                        ordinal_options['y_name'] = f'Probability of {ordinal_category}'
                    if not ordinal_options.get('moderator_separation'):
                        ordinal_options['moderator_separation'] = 'mean'
                    
                    # Use pre-generated predictions for fast plotting
                    spotlight_json = _generate_multinomial_ordinal_spotlight_from_predictions(
                        session.ordinal_predictions[interaction], 
                        interaction, 
                        ordinal_category, 
                        ordinal_options
                    )
                else:
                    # For custom separation method or std dev multiplier, regenerate predictions on the fly
                    print(f"DEBUG: Regenerating ordinal spotlight with custom parameters - separation: {separation_method}, std_dev_multiplier: {std_dev_multiplier}")
                    print(f"DEBUG: Ordinal category being passed to regeneration: {ordinal_category}")
                    spotlight_json = generate_spotlight_for_interaction(
                        fitted_model, df, interaction, custom_options, is_ordinal=is_ordinal
                    )
            else:
                # Fall back to regular generation (will show category selection)
                # Parse interaction to get variable names for proper labeling
                if "*" in interaction:
                    parts = [p.strip() for p in interaction.split("*")]
                    if len(parts) >= 2:
                        x_var, moderator_var = parts[0], parts[1]
                    else:
                        x_var, moderator_var = interaction, "Moderator"
                else:
                    parts = interaction.split(":")
                    if len(parts) >= 2:
                        x_var, moderator_var = parts[0].strip(), parts[1].strip()
                    else:
                        x_var, moderator_var = interaction, "Moderator"
                
                # Set default variable names if not provided
                fallback_options = custom_options.copy()
                if not fallback_options.get('x_name'):
                    fallback_options['x_name'] = x_var
                if not fallback_options.get('moderator_display_name'):
                    fallback_options['moderator_display_name'] = moderator_var
                if not fallback_options.get('y_name'):
                    fallback_options['y_name'] = 'Predicted Probability'
                if not fallback_options.get('moderator_separation'):
                    fallback_options['moderator_separation'] = 'mean'
                
                spotlight_json = generate_spotlight_for_interaction(
                    fitted_model, df, interaction, fallback_options, is_ordinal=is_ordinal
                )
        # For multinomial regression, always use regular generation to ensure category selection works
        elif is_multinomial:
            print(f"DEBUG: Multinomial regression detected, using regular generation")
            multinomial_category = custom_options.get('multinomial_category')
            print(f"DEBUG: multinomial_category = {multinomial_category}")
            print(f"DEBUG: interaction = {interaction}")
            print(f"DEBUG: is_multinomial = {is_multinomial}")
            
            spotlight_json = generate_spotlight_for_interaction(
                fitted_model, df, interaction, custom_options, is_multinomial=is_multinomial
            )
        else:
            # Generate spotlight plot for the specific interaction
            spotlight_json = generate_spotlight_for_interaction(
                fitted_model, df, interaction, custom_options, is_ordinal=is_ordinal, is_multinomial=is_multinomial
            )
        
        if spotlight_json:
            # Check if it's a special response (like ordinal category selection)
            if isinstance(spotlight_json, dict) and 'type' in spotlight_json:
                return JsonResponse(spotlight_json)
            else:
                return HttpResponse(spotlight_json, content_type='application/json')
        else:
            # Parse interaction to get more specific error
            if "*" in interaction:
                x, m = [p.strip() for p in interaction.split("*", 1)]
            else:
                parts = interaction.split(":")
                if len(parts) == 2:
                    x, m = parts[0].strip(), parts[1].strip()
                else:
                    return HttpResponse(f'Invalid interaction format: {interaction}', status=500)
            
            # Check which variable is missing
            if x not in df.columns:
                return HttpResponse(f'Variable "{x}" not found in dataset. Available columns: {list(df.columns)}', status=500)
            
            # Check original moderator variable (custom moderator is just for display)
            if m not in df.columns:
                return HttpResponse(f'Moderator variable "{m}" not found in dataset. Available columns: {list(df.columns)}', status=500)
            
            return HttpResponse('Failed to generate spotlight plot - unknown error', status=500)
            
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        return HttpResponse(error_msg, status=500)


def generate_correlation_heatmap(request, session_id):
    """Generate correlation heatmap for continuous variables."""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    session = get_object_or_404(AnalysisSession, pk=session_id)
    
    try:
        # Load the dataset
        df, schema_types, schema_orders = _read_dataset_file(session.dataset.file_path)
        
        # Get continuous variables from the equation (default behavior)
        continuous_vars = _get_continuous_variables_from_formula(df, session.formula)
        
        # If no continuous variables in equation, fall back to all continuous variables
        if len(continuous_vars) < 2:
            continuous_vars = _get_continuous_variables(df)
            if len(continuous_vars) < 2:
                return HttpResponse('Need at least 2 continuous variables for correlation heatmap', status=400)
        
        # Get selected variables from request
        x_vars = request.POST.getlist('x_vars[]')
        y_vars = request.POST.getlist('y_vars[]')
        
        # If no variables selected, use all continuous variables
        if not x_vars:
            x_vars = continuous_vars.copy()
        if not y_vars:
            y_vars = continuous_vars.copy()
        
        # Filter to only include variables that exist in the dataset
        x_vars = [var for var in x_vars if var in df.columns and pd.api.types.is_numeric_dtype(df[var])]
        y_vars = [var for var in y_vars if var in df.columns and pd.api.types.is_numeric_dtype(df[var])]
        
        if len(x_vars) < 1 or len(y_vars) < 1:
            return HttpResponse('Need at least 1 variable for each axis', status=400)
        
        # Create options for the heatmap
        options = {
            'show_significance': request.POST.get('show_significance', 'true').lower() == 'true',
            'color_scheme': request.POST.get('color_scheme', 'RdBu')
        }
        
        # Generate heatmap for selected variables
        heatmap_json = _build_correlation_heatmap_json(df, x_vars, y_vars, options)
        
        if heatmap_json:
            return HttpResponse(heatmap_json, content_type='application/json')
        else:
            return HttpResponse('Failed to generate correlation heatmap', status=500)
            
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        return HttpResponse(error_msg, status=500)



def merge_datasets(request):
    """API endpoint to merge multiple datasets based on common column values"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        data = json.loads(request.body)
        dataset_ids = data.get('datasets', [])
        merge_columns = data.get('merge_columns', [])
        
        if len(dataset_ids) < 2:
            return JsonResponse({'error': 'At least 2 datasets required for merge'}, status=400)
        
        if len(merge_columns) != len(dataset_ids):
            return JsonResponse({'error': 'Must specify merge column for each dataset'}, status=400)
        
        # Load datasets
        datasets = []
        dataframes = []
        
        for i, dataset_id in enumerate(dataset_ids):
            try:
                dataset = get_object_or_404(Dataset, pk=dataset_id)
                datasets.append(dataset)
                
                # Read dataset file
                df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
                dataframes.append(df)
                
            except Exception as e:
                return JsonResponse({'error': f'Error loading dataset {dataset_id}: {str(e)}'}, status=400)
        
        # Perform merge
        try:
            # Start with the first dataset
            merged_df = dataframes[0].copy()
            merge_column_1 = merge_columns[0]['column']
            
            # Merge with each subsequent dataset
            for i in range(1, len(dataframes)):
                df = dataframes[i]
                merge_column_2 = merge_columns[i]['column']
                
                # Check if merge columns exist
                if merge_column_1 not in merged_df.columns:
                    return JsonResponse({'error': f'Column "{merge_column_1}" not found in first dataset'}, status=400)
                
                if merge_column_2 not in df.columns:
                    return JsonResponse({'error': f'Column "{merge_column_2}" not found in dataset {datasets[i].name}'}, status=400)
                
                # Check data types before merging
                col1_type = str(merged_df[merge_column_1].dtype)
                col2_type = str(df[merge_column_2].dtype)
                
                if col1_type != col2_type:
                    return JsonResponse({
                        'error': f'These two columns don\'t have common values. Column "{merge_column_1}" has {col1_type} data type while column "{merge_column_2}" has {col2_type} data type. Please select columns with the same data type.'
                    }, status=400)
                
                # Perform inner join
                merged_df = pd.merge(
                    merged_df, 
                    df, 
                    left_on=merge_column_1, 
                    right_on=merge_column_2, 
                    how='inner',
                    suffixes=('', f'_from_{datasets[i].name.replace(" ", "_")}')
                )
                
                # Remove duplicate merge columns (keep the first one)
                if merge_column_1 != merge_column_2:
                    merged_df = merged_df.drop(columns=[merge_column_2])
        
        except Exception as e:
            error_msg = str(e)
            # Check for specific pandas merge errors
            if "int64" in error_msg and "object" in error_msg:
                return JsonResponse({
                    'error': 'These two columns don\'t have common values. Please select columns with the same data type.'
                }, status=400)
            else:
                return JsonResponse({'error': f'Error merging datasets: {error_msg}'}, status=400)
        
        # Create new dataset
        try:
            # Generate unique filename
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            merged_filename = f"merged_{unique_id}.csv"
            merged_file_path = os.path.join(settings.MEDIA_ROOT, merged_filename)
            
            # Save merged dataset
            merged_df.to_csv(merged_file_path, index=False)
            
            # Create dataset record
            merged_dataset = Dataset.objects.create(
                name=merged_filename,
                file_path=merged_file_path
            )
            
            # Generate dataset name
            dataset_names = [d.name for d in datasets]
            merged_dataset_name = f"merged_{'_'.join(dataset_names[:2])}"
            if len(dataset_names) > 2:
                merged_dataset_name += f"_and_{len(dataset_names)-2}_more"
            
            # Update dataset name
            merged_dataset.name = merged_dataset_name
            merged_dataset.save()
            
            return JsonResponse({
                'success': True,
                'dataset_id': merged_dataset.id,
                'dataset_name': merged_dataset.name,
                'rows': len(merged_df),
                'columns': len(merged_df.columns)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error saving merged dataset: {str(e)}'}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


def cancel_bayesian_analysis(request):
    """Cancel a running Bayesian analysis"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            # Cancel specific session
            session = get_object_or_404(AnalysisSession, pk=session_id)
            
            # Instead of marking as cancelled, we'll just return success
            # The frontend will reload to show the previous state
            return JsonResponse({
                'success': True,
                'message': f'Analysis for session {session.name} has been cancelled'
            })
        else:
            # Cancel any running Bayesian analysis (from index page)
            # This is a simplified approach - in a real implementation,
            # you might want to track running processes more precisely
            return JsonResponse({
                'success': True,
                'message': 'Bayesian analysis cancellation requested'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error cancelling analysis: {str(e)}'}, status=500)

def run_bma_analysis(request):
    """Handle BMA analysis requests"""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')  # 'new' or 'update'
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        categorical_vars = request.POST.get('categorical_vars', '')
        session_name = request.POST.get('session_name') or f"BMA Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Import BMA module
        from models.BMA import BMAModule
        
        # Create BMA module instance
        bma_module = BMAModule()
        
        # Prepare options
        options = {}
        if categorical_vars:
            options['categorical_vars'] = categorical_vars
        
        # Run BMA analysis
        result = bma_module.run(df, formula, options)
        
        if not result['success']:
            return render(request, 'engine/BMA_results.html', {
                'dataset': dataset,
                'session': get_object_or_404(AnalysisSession, pk=session_id) if (action == 'update' and session_id) else None,
                'formula': formula,
                'results': {'has_results': False, 'error': result['error']}
            })
        
        # Format results for template
        formatted_results = result['results']
        
        # Update existing session or create new one
        if action == 'update' and session_id:
            print(f"DEBUG: Updating existing BMA session {session_id}")
            session = get_object_or_404(AnalysisSession, pk=session_id)
            session.name = session_name
            session.module = 'bma'
            session.formula = formula
            session.analysis_type = 'bma'
            session.options = options
            session.dataset = dataset
            # Ensure user is set if not already set
            if not session.user and request.user.is_authenticated:
                session.user = request.user
            session.save()
        else:
            print(f"DEBUG: Creating new BMA session (action: {action}, session_id: {session_id})")
            # Check session limits for new sessions
            user = request.user if request.user.is_authenticated else None
            if user:
                profile = user.profile
                limits = profile.get_limits()
                if limits['sessions'] != -1:
                    current_count = user.sessions.count()
                    if current_count >= limits['sessions']:
                        return render(request, 'engine/BMA_results.html', {
                            'dataset': dataset,
                            'session': None,
                            'formula': formula,
                            'results': {
                                'has_results': False,
                                'error': f"You have reached your session limit ({limits['sessions']} sessions). Please delete some sessions or upgrade your plan."
                            }
                        })
            # Associate session with user if authenticated
            session = AnalysisSession(
                name=session_name,
                module='bma',
                formula=formula,
                analysis_type='bma',
                options=options,
                dataset=dataset,
                user=user
            )
            session.save()
        
        # Track BMA analysis in history
        try:
            iteration_type = 'update' if action == 'update' and session_id else 'initial'
            track_session_iteration(
                session_id=session.id,
                iteration_type=iteration_type,
                equation=formula,
                analysis_type='bma',
                results_data=formatted_results,
                plots_added=[],
                modifications={
                    'categorical_vars': categorical_vars,
                    'module': 'bma'
                },
                notes="BMA analysis completed successfully"
            )
        except Exception as e:
            print(f"Failed to track BMA session history: {e}")
        
        return render(request, 'engine/BMA_results.html', {
            'dataset': dataset,
            'session': session,  # Add session to context
            'formula': formula,
            'results': formatted_results
        })
        
    except Exception as e:
        return render(request, 'engine/BMA_results.html', {
            'dataset': None,
            'formula': request.POST.get('formula', ''),
            'results': {'has_results': False, 'error': str(e)}
        })


def generate_anova_plot_view(request, session_id):
    """Generate ANOVA plot with t-tests"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        session = get_object_or_404(AnalysisSession, pk=session_id)
        
        # Parse JSON body
        import json
        data = json.loads(request.body)
        
        x_var = data.get('x_var')
        y_var = data.get('y_var')
        group_var = data.get('group_var')
        x_std = float(data.get('x_std', 1.0))
        group_std = float(data.get('group_std', 1.0))
        sig_level = float(data.get('sig_level', 0.05))
        
        if not x_var or not y_var:
            return JsonResponse({'success': False, 'error': 'X and Y variables required'}, status=400)
        
        # Load dataset
        df, column_types, schema_orders = _read_dataset_file(session.dataset.file_path)
        
        # Import plot generation function
        from models.ANOVA import generate_anova_plot
        
        # Generate the plot
        result = generate_anova_plot(df, x_var, y_var, group_var, x_std, group_std, sig_level)
        
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Unknown error')}, status=400)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def run_anova_analysis(request):
    """Handle ANOVA analysis requests"""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')  # 'new' or 'update'
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        session_name = request.POST.get('session_name') or f"ANOVA Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Import ANOVA module
        from models.ANOVA import ANOVAModule
        
        # Create ANOVA module instance
        anova_module = ANOVAModule()
        
        # Prepare options
        options = {}
        
        # Run ANOVA analysis
        result = anova_module.run(df, formula, None, None, options, column_types, schema_orders)
        
        if not result.get('has_results', False):
            return render(request, 'engine/ANOVA_results.html', {
                'dataset': dataset,
                'session': get_object_or_404(AnalysisSession, pk=session_id) if (action == 'update' and session_id) else None,
                'formula': formula,
                'results': {'has_results': False, 'error': result.get('error', 'Unknown error')}
            })
        
        # Update existing session or create new one
        if action == 'update' and session_id:
            print(f"DEBUG: Updating existing ANOVA session {session_id}")
            session = get_object_or_404(AnalysisSession, pk=session_id)
            session.name = session_name
            session.module = 'anova'
            session.formula = formula
            session.analysis_type = 'anova'
            session.options = options
            session.dataset = dataset
            # Ensure user is set if not already set
            if not session.user and request.user.is_authenticated:
                session.user = request.user
            session.save()
        else:
            print(f"DEBUG: Creating new ANOVA session (action: {action}, session_id: {session_id})")
            # Check session limits for new sessions
            user = request.user if request.user.is_authenticated else None
            if user:
                profile = user.profile
                limits = profile.get_limits()
                if limits['sessions'] != -1:
                    current_count = user.sessions.count()
                    if current_count >= limits['sessions']:
                        return render(request, 'engine/ANOVA_results.html', {
                            'dataset': dataset,
                            'session': None,
                            'formula': formula,
                            'results': {
                                'has_results': False,
                                'error': f"You have reached your session limit ({limits['sessions']} sessions). Please delete some sessions or upgrade your plan."
                            }
                        })
            # Associate session with user if authenticated
            session = AnalysisSession(
                name=session_name,
                module='anova',
                formula=formula,
                analysis_type='anova',
                options=options,
                dataset=dataset,
                user=user
            )
            session.save()
        
        # Track ANOVA analysis in history
        try:
            iteration_type = 'update' if action == 'update' and session_id else 'initial'
            track_session_iteration(
                session_id=session.id,
                iteration_type=iteration_type,
                equation=formula,
                analysis_type='anova',
                results_data=result,
                plots_added=[],
                modifications={
                    'module': 'anova'
                },
                notes="ANOVA analysis completed successfully"
            )
        except Exception as e:
            print(f"Failed to track ANOVA session history: {e}")
        
        # Get numeric variables for the plot form
        numeric_vars = result.get('numeric_vars', [])
        
        return render(request, 'engine/ANOVA_results.html', {
            'dataset': dataset,
            'session': session,
            'formula': formula,
            'results': result,
            'numeric_vars': numeric_vars
        })
        
    except Exception as e:
        return render(request, 'engine/ANOVA_results.html', {
            'dataset': None,
            'session': None,
            'formula': request.POST.get('formula', ''),
            'results': {'has_results': False, 'error': str(e)},
            'numeric_vars': []
        })


def run_varx_analysis(request):
    """Handle VARX analysis requests"""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        # Get parameters from request
        action = request.POST.get('action', 'new')  # 'new' or 'update'
        session_id = request.POST.get('session_id')
        dataset_id = request.POST.get('dataset_id')
        formula = request.POST.get('formula', '')
        session_name = request.POST.get('session_name') or f"VARX Analysis {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if not dataset_id:
            return HttpResponse('Please select a dataset', status=400)
        
        if not formula:
            return HttpResponse('Please enter a formula', status=400)
        
        # Get dataset
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        
        # Import VARX module
        from models.VARX import VARXModule
        
        # Create VARX module instance
        varx_module = VARXModule()
        
        # Prepare options (get VAR order from request)
        # If var_order is not provided or is 'auto', use automatic selection
        var_order_input = request.POST.get('var_order', None)
        max_lags_input = request.POST.get('max_lags', 10)
        
        # Get max_lags (default to 10)
        try:
            max_lags = int(max_lags_input)
        except (ValueError, TypeError):
            max_lags = 10
        
        if var_order_input and var_order_input != 'auto' and var_order_input != '0':
            try:
                var_order = int(var_order_input)
                options = {'var_order': var_order, 'max_lags': max_lags}
            except (ValueError, TypeError):
                options = {'var_order': 'auto', 'max_lags': max_lags}  # Use auto-selection
        else:
            # Use automatic lag selection
            options = {'var_order': 'auto', 'max_lags': max_lags}
        
        # Run VARX analysis
        result = varx_module.run(df, formula, None, None, options, column_types, schema_orders)
        
        if not result.get('has_results', False):
            return render(request, 'engine/VARX_results.html', {
                'dataset': dataset,
                'session': get_object_or_404(AnalysisSession, pk=session_id) if (action == 'update' and session_id) else None,
                'formula': formula,
                'results': {'has_results': False, 'error': result.get('error', 'Unknown error')}
            })
        
        # Update existing session or create new one
        if action == 'update' and session_id:
            print(f"DEBUG: Updating existing VARX session {session_id}")
            session = get_object_or_404(AnalysisSession, pk=session_id)
            session.name = session_name
            session.module = 'varx'
            session.formula = formula
            session.analysis_type = 'varx'
            session.options = options
            session.dataset = dataset
            # Ensure user is set if not already set
            if not session.user and request.user.is_authenticated:
                session.user = request.user
            session.save()
        else:
            print(f"DEBUG: Creating new VARX session (action: {action}, session_id: {session_id})")
            # Check session limits for new sessions
            user = request.user if request.user.is_authenticated else None
            if user:
                profile = user.profile
                limits = profile.get_limits()
                if limits['sessions'] != -1:
                    current_count = user.sessions.count()
                    if current_count >= limits['sessions']:
                        return render(request, 'engine/VARX_results.html', {
                            'dataset': dataset,
                            'session': None,
                            'formula': formula,
                            'results': {
                                'has_results': False,
                                'error': f"You have reached your session limit ({limits['sessions']} sessions). Please delete some sessions or upgrade your plan."
                            }
                        })
            # Associate session with user if authenticated
            session = AnalysisSession(
                name=session_name,
                module='varx',
                formula=formula,
                analysis_type='varx',
                options=options,
                dataset=dataset,
                user=user
            )
            session.save()
        
        # Store model results for IRF generation (pickle the results object)
        try:
            import pickle
            if result.get('model_results'):
                session.fitted_model = pickle.dumps({
                    'model_results': result['model_results'],
                    'endog_data': result.get('endog_data'),
                    'dependent_vars': result.get('dependent_vars'),
                    'independent_vars': result.get('independent_vars')
                })
                session.save()
        except Exception as e:
            print(f"Failed to store VARX model for IRF: {e}")
        
        # Track VARX analysis in history
        try:
            iteration_type = 'update' if action == 'update' and session_id else 'initial'
            # Get var_order from result or options
            var_order_for_history = result.get('var_order') or options.get('var_order') or 'auto'
            track_session_iteration(
                session_id=session.id,
                iteration_type=iteration_type,
                equation=formula,
                analysis_type='varx',
                results_data=result,
                plots_added=[],
                modifications={
                    'module': 'varx',
                    'var_order': var_order_for_history
                },
                notes="VARX analysis completed successfully"
            )
        except Exception as e:
            print(f"Failed to track VARX session history: {e}")
        
        return render(request, 'engine/VARX_results.html', {
            'dataset': dataset,
            'session': session,
            'formula': formula,
            'results': result
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render(request, 'engine/VARX_results.html', {
            'dataset': None,
            'session': None,
            'formula': request.POST.get('formula', ''),
            'results': {'has_results': False, 'error': str(e)}
        })


@csrf_exempt
@require_http_methods(["POST"])
def generate_varx_irf_view(request, session_id):
    """Generate VARX IRF plot"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        session = get_object_or_404(AnalysisSession, pk=session_id)
        
        # Parse JSON body
        import json
        data = json.loads(request.body)
        
        irf_horizon = int(data.get('irf_horizon', 10))
        
        if irf_horizon < 1 or irf_horizon > 50:
            return JsonResponse({'success': False, 'error': 'IRF horizon must be between 1 and 50'}, status=400)
        
        # Load stored model results
        if not session.fitted_model:
            return JsonResponse({'success': False, 'error': 'No fitted model found. Please run VARX analysis first.'}, status=400)
        
        try:
            import pickle
            model_data = pickle.loads(session.fitted_model)
            model_results = model_data['model_results']
            endog_data = model_data['endog_data']
            dependent_vars = model_data['dependent_vars']
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to load model: {str(e)}'}, status=400)
        
        # Get IRF parameters from request
        response_var = data.get('response_var', None)  # Which variable responds
        shock_var = data.get('shock_var', None)  # Which variable is shocked
        shock_type = data.get('shock_type', 'orthogonal')  # 'orthogonal' or 'generalized'
        show_ci = data.get('show_ci', False)  # Whether to show 95% CI bands
        
        # Generate IRF
        try:
            # VAR uses irf() method, not impulse_responses()
            # For orthogonal shocks, use orth_irfs
            # For generalized (Pesaran-Shin), use irfs
            irf_obj = model_results.irf(irf_horizon)
            
            if shock_type == 'orthogonal':
                # Orthogonalized IRF
                irf = irf_obj.orth_irfs
            else:
                # Generalized IRF (Pesaran-Shin)
                irf = irf_obj.irfs
            
            # Store original IRF before filtering (for CI calculation)
            irf_full = irf.copy() if hasattr(irf, 'copy') else irf
            
            # If specific shock_var is selected, filter to that shock
            # irf shape is (steps+1, n_vars, n_vars) where [step, response, shock]
            # Store whether we filtered, but keep track for CI indexing
            shock_idx_filtered = None
            if shock_var and shock_var in dependent_vars:
                shock_idx_filtered = dependent_vars.index(shock_var)
                # Extract only the columns for this shock: irf[:, :, shock_idx]
                irf = irf[:, :, shock_idx_filtered]
            
            # If specific response_var is selected, filter to that response
            # Store whether we filtered for CI indexing
            response_idx_filtered = None
            if response_var and response_var in dependent_vars:
                response_idx_filtered = dependent_vars.index(response_var)
                # If irf is 3D, extract response: irf[:, response_idx, :]
                # If irf is 2D (after shock filtering), extract response: irf[:, response_idx]
                if len(irf.shape) == 3:
                    irf = irf[:, response_idx_filtered, :]
                elif len(irf.shape) == 2:
                    irf = irf[:, response_idx_filtered:response_idx_filtered+1]  # Keep 2D shape
            
            # IRF shape: (steps+1, n_vars, n_vars) or (steps+1, n_vars) if impulse is specified
            # If impulse is specified, shape is (steps+1, n_vars) - each column is response of one variable
            # If impulse is None, shape is (steps+1, n_vars, n_vars) - [step, response_var, shock_var]
            
            # Calculate confidence intervals if requested
            # IMPORTANT: Calculate CI on the FULL IRF array (before filtering) to get CIs for all variables
            irf_ci_lower = None
            irf_ci_upper = None
            if show_ci:
                try:
                    import scipy.stats as stats
                    import numpy as np
                    import pandas as pd
                    
                    # Try to get standard errors from IRF object
                    # Note: statsmodels VAR IRF may not have direct stderr attributes
                    irf_stderr = None
                    
                    # Check if IRF object has standard error methods
                    if hasattr(irf_obj, 'stderr_orth_irfs') and shock_type == 'orthogonal':
                        try:
                            irf_stderr = irf_obj.stderr_orth_irfs
                            print(f"DEBUG: Using stderr_orth_irfs, shape: {irf_stderr.shape}")
                        except:
                            pass
                    elif hasattr(irf_obj, 'stderr_irfs') and shock_type != 'orthogonal':
                        try:
                            irf_stderr = irf_obj.stderr_irfs
                            print(f"DEBUG: Using stderr_irfs, shape: {irf_stderr.shape}")
                        except:
                            pass
                    
                    # If standard errors not available, use approximation based on parameter SEs
                    if irf_stderr is None:
                        print("DEBUG: Standard errors not available from IRF object, using approximation")
                        # Get parameter standard errors
                        param_std = model_results.bse
                        if isinstance(param_std, (pd.DataFrame, pd.Series)):
                            # Get mean of all parameter standard errors
                            avg_std = float(param_std.values.mean()) if len(param_std) > 0 else 0.1
                        else:
                            avg_std = float(np.mean(param_std)) if len(param_std) > 0 else 0.1
                        
                        # Convert FULL IRF to numpy array (before filtering) for CI calculation
                        irf_array_temp = np.asarray(irf_full)
                        
                        # Approximate uncertainty: increases with horizon
                        # Use a conservative approximation: std_err = avg_param_std * sqrt(horizon + 1)
                        std_approx = avg_std * np.sqrt(np.arange(irf_horizon + 1) + 1)
                        
                        # Create stderr array with same shape as FULL IRF (before filtering)
                        if len(irf_array_temp.shape) == 2:
                            # 2D: (steps+1, n_vars)
                            irf_stderr = std_approx[:, np.newaxis]
                        elif len(irf_array_temp.shape) == 3:
                            # 3D: (steps+1, n_vars, n_vars)
                            irf_stderr = std_approx[:, np.newaxis, np.newaxis]
                        else:
                            irf_stderr = std_approx
                        
                        print(f"DEBUG: Using approximated stderr, shape: {irf_stderr.shape}, avg_std: {avg_std}")
                    
                    # Calculate CI on FULL IRF array (before filtering) to get CIs for all variables
                    if irf_stderr is not None:
                        # Calculate 95% CI: ±1.96 * std_err
                        z_critical = stats.norm.ppf(0.975)  # 1.96 for 95% CI
                        
                        # Convert FULL IRF to numpy array for calculations
                        irf_array_temp = np.asarray(irf_full)
                        irf_stderr_array = np.asarray(irf_stderr)
                        
                        # Ensure shapes match (broadcast if needed)
                        if irf_array_temp.shape != irf_stderr_array.shape:
                            print(f"DEBUG: Shape mismatch - Full IRF: {irf_array_temp.shape}, stderr: {irf_stderr_array.shape}")
                            try:
                                # Try to broadcast stderr to match IRF shape
                                irf_stderr_array = np.broadcast_to(irf_stderr_array, irf_array_temp.shape).copy()
                                print(f"DEBUG: After broadcasting, stderr shape: {irf_stderr_array.shape}")
                            except Exception as e:
                                print(f"DEBUG: Could not broadcast stderr: {e}")
                                irf_stderr = None
                        
                        if irf_stderr is not None:
                            # Calculate CI bounds on FULL IRF (before filtering)
                            irf_ci_lower = irf_array_temp - z_critical * irf_stderr_array
                            irf_ci_upper = irf_array_temp + z_critical * irf_stderr_array
                            print(f"DEBUG: CI calculated on full IRF successfully")
                            print(f"DEBUG: CI shapes - lower: {irf_ci_lower.shape}, upper: {irf_ci_upper.shape}")
                            
                            # Now apply same filtering to CI arrays as was applied to IRF
                            if shock_idx_filtered is not None:
                                if len(irf_ci_lower.shape) == 3:
                                    irf_ci_lower = irf_ci_lower[:, :, shock_idx_filtered]
                                    irf_ci_upper = irf_ci_upper[:, :, shock_idx_filtered]
                                    print(f"DEBUG: After shock filtering CI, shape: {irf_ci_lower.shape}")
                            if response_idx_filtered is not None:
                                if len(irf_ci_lower.shape) == 3:
                                    irf_ci_lower = irf_ci_lower[:, response_idx_filtered, :]
                                    irf_ci_upper = irf_ci_upper[:, response_idx_filtered, :]
                                    print(f"DEBUG: After response filtering CI (3D), shape: {irf_ci_lower.shape}")
                                elif len(irf_ci_lower.shape) == 2:
                                    irf_ci_lower = irf_ci_lower[:, response_idx_filtered:response_idx_filtered+1]
                                    irf_ci_upper = irf_ci_upper[:, response_idx_filtered:response_idx_filtered+1]
                                    print(f"DEBUG: After response filtering CI (2D), shape: {irf_ci_lower.shape}")
                        else:
                            print("DEBUG: Could not calculate CI - stderr is None after filtering")
                    else:
                        print("DEBUG: Could not calculate CI - stderr is None")
                        
                except Exception as e:
                    print(f"Warning: Could not calculate CI for IRF: {e}")
                    import traceback
                    traceback.print_exc()
                    irf_ci_lower = None
                    irf_ci_upper = None
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Failed to generate IRF: {str(e)}'}, status=400)
        
        # Create Plotly figures
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Determine which variables to plot
        response_vars_to_plot = [response_var] if response_var and response_var in dependent_vars else dependent_vars
        shock_vars_to_plot = [shock_var] if shock_var and shock_var in dependent_vars else dependent_vars
        
        # Create subplots - one for each response variable
        n_response_vars = len(response_vars_to_plot)
        fig = make_subplots(
            rows=n_response_vars, cols=1,
            subplot_titles=[f'Response of {var} to Shocks' for var in response_vars_to_plot],
            vertical_spacing=0.1
        )
        
        periods = list(range(irf_horizon + 1))
        
        # Handle different IRF array shapes
        # Convert to numpy array for easier manipulation
        import numpy as np
        irf_array = np.asarray(irf)
        
        print(f"DEBUG: IRF shape: {irf_array.shape}, n_vars: {len(dependent_vars)}, steps: {irf_horizon}")
        
        if len(irf_array.shape) == 2:
            # Shape: (steps+1, n_vars) - impulse was specified
            # Each column is the response of one variable to the specified shock
            # irf[step, response_var_idx]
            for i, response_var_name in enumerate(dependent_vars):
                if response_var_name in response_vars_to_plot:
                    row_idx = response_vars_to_plot.index(response_var_name) + 1
                    try:
                        # Access as irf[step, variable_index]
                        response_data = irf_array[:, i] if i < irf_array.shape[1] else irf_array[:, 0]
                        response_list = response_data.tolist() if hasattr(response_data, 'tolist') else list(response_data)
                        
                        # Add main IRF line
                        fig.add_trace(
                            go.Scatter(
                                x=periods,
                                y=response_list,
                                mode='lines+markers',
                                name=f'Response to {shock_var or "shock"}',
                                line=dict(width=2),
                                marker=dict(size=4)
                            ),
                            row=row_idx, col=1
                        )
                        
                        # Add CI bands if requested
                        if show_ci and irf_ci_lower is not None and irf_ci_upper is not None:
                            # Determine correct index for CI arrays
                            # If response_var was filtered, CI arrays only have 1 column (index 0)
                            # Otherwise, CI arrays have all variables (use index i)
                            if response_idx_filtered is not None:
                                # Response was filtered - CI arrays only have the filtered variable
                                ci_idx = 0
                            else:
                                # Response was not filtered - CI arrays have all variables
                                ci_idx = i if i < irf_ci_lower.shape[1] else 0
                            
                            # Handle different CI array shapes
                            if len(irf_ci_lower.shape) == 2:
                                # 2D: (steps+1, n_vars) or (steps+1, 1) if filtered
                                ci_lower = irf_ci_lower[:, ci_idx] if ci_idx < irf_ci_lower.shape[1] else irf_ci_lower[:, 0]
                                ci_upper = irf_ci_upper[:, ci_idx] if ci_idx < irf_ci_upper.shape[1] else irf_ci_upper[:, 0]
                            elif len(irf_ci_lower.shape) == 1:
                                # 1D: (steps+1) - single variable after filtering
                                ci_lower = irf_ci_lower
                                ci_upper = irf_ci_upper
                            else:
                                # Unexpected shape, skip CI for this variable
                                print(f"DEBUG: Unexpected CI shape for variable {i}: {irf_ci_lower.shape}")
                                continue
                            
                            ci_lower_list = ci_lower.tolist() if hasattr(ci_lower, 'tolist') else list(ci_lower)
                            ci_upper_list = ci_upper.tolist() if hasattr(ci_upper, 'tolist') else list(ci_upper)
                            
                            print(f"DEBUG: Adding CI for variable {i} ({response_var_name}), ci_idx={ci_idx}, CI shape: {irf_ci_lower.shape}")
                            
                            # Add upper CI band
                            fig.add_trace(
                                go.Scatter(
                                    x=periods,
                                    y=ci_upper_list,
                                    mode='lines',
                                    name='95% CI Upper',
                                    line=dict(width=0),
                                    showlegend=(row_idx == 1),  # Only show legend for first subplot
                                    hoverinfo='skip'
                                ),
                                row=row_idx, col=1
                            )
                            
                            # Add lower CI band with fill
                            fig.add_trace(
                                go.Scatter(
                                    x=periods,
                                    y=ci_lower_list,
                                    mode='lines',
                                    name='95% CI',
                                    line=dict(width=0),
                                    fill='tonexty',
                                    fillcolor='rgba(0, 100, 255, 0.2)',
                                    showlegend=False,
                                    hoverinfo='skip'
                                ),
                                row=row_idx, col=1
                            )
                    except (IndexError, TypeError) as e:
                        print(f"Warning: Could not access irf[:, {i}], shape: {irf_array.shape}, error: {e}")
                        continue
            
            # Add zero line for each subplot
            for row_idx in range(1, n_response_vars + 1):
                fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=row_idx, col=1)
            
            # Update y-axis labels
            for row_idx in range(1, n_response_vars + 1):
                fig.update_yaxes(title_text="Response", row=row_idx, col=1)
        elif len(irf_array.shape) == 3:
            # Shape: (steps+1, n_vars, n_vars) - all combinations
            # irf[step, response_var_idx, shock_var_idx]
            for i, response_var_name in enumerate(dependent_vars):
                if response_var_name in response_vars_to_plot:
                    row_idx = response_vars_to_plot.index(response_var_name) + 1
                    
                    # Plot response to each shock variable
                    for j, shock_var_name in enumerate(dependent_vars):
                        if shock_var_name in shock_vars_to_plot:
                            try:
                                # Access as irf[step, response_idx, shock_idx]
                                if i < irf_array.shape[1] and j < irf_array.shape[2]:
                                    response_data = irf_array[:, i, j]
                                    response_list = response_data.tolist() if hasattr(response_data, 'tolist') else list(response_data)
                                    
                                    # Add main IRF line
                                    fig.add_trace(
                                        go.Scatter(
                                            x=periods,
                                            y=response_list,
                                            mode='lines+markers',
                                            name=f'Response to {shock_var_name}',
                                            line=dict(width=2),
                                            marker=dict(size=4)
                                        ),
                                        row=row_idx, col=1
                                    )
                                    
                                    # Add CI bands if requested
                                    if show_ci and irf_ci_lower is not None and irf_ci_upper is not None:
                                        # Determine correct indices based on filtering
                                        # Use the stored filtered indices to determine what was filtered
                                        if len(irf_ci_lower.shape) == 3:
                                            # 3D: (steps+1, n_vars, n_vars) - no filtering or only partial
                                            # Use original indices i and j
                                            if i < irf_ci_lower.shape[1] and j < irf_ci_lower.shape[2]:
                                                ci_lower = irf_ci_lower[:, i, j]
                                                ci_upper = irf_ci_upper[:, i, j]
                                            else:
                                                # Index out of bounds, skip CI for this combination
                                                print(f"DEBUG: CI index out of bounds: i={i}, j={j}, shape={irf_ci_lower.shape}")
                                                continue
                                        elif len(irf_ci_lower.shape) == 2:
                                            # 2D: (steps+1, n_vars) - filtered by shock or response
                                            # Determine which dimension was filtered
                                            if response_idx_filtered is not None and shock_idx_filtered is not None:
                                                # Both filtered - should be 1D, but handle 2D case
                                                ci_idx = 0
                                            elif response_idx_filtered is not None:
                                                # Response filtered - CI has shape (steps+1, n_shocks)
                                                # Use shock index j
                                                ci_idx = j if j < irf_ci_lower.shape[1] else 0
                                            elif shock_idx_filtered is not None:
                                                # Shock filtered - CI has shape (steps+1, n_responses)
                                                # Use response index i
                                                ci_idx = i if i < irf_ci_lower.shape[1] else 0
                                            else:
                                                # Shouldn't happen - no filtering but 2D shape
                                                ci_idx = i if i < irf_ci_lower.shape[1] else 0
                                            
                                            ci_lower = irf_ci_lower[:, ci_idx] if ci_idx < irf_ci_lower.shape[1] else irf_ci_lower[:, 0]
                                            ci_upper = irf_ci_upper[:, ci_idx] if ci_idx < irf_ci_upper.shape[1] else irf_ci_upper[:, 0]
                                        elif len(irf_ci_lower.shape) == 1:
                                            # 1D: (steps+1) - both filtered, use directly
                                            ci_lower = irf_ci_lower
                                            ci_upper = irf_ci_upper
                                        else:
                                            # Unexpected shape, skip CI
                                            print(f"DEBUG: Unexpected CI shape: {irf_ci_lower.shape}")
                                            continue
                                        
                                        ci_lower_list = ci_lower.tolist() if hasattr(ci_lower, 'tolist') else list(ci_lower)
                                        ci_upper_list = ci_upper.tolist() if hasattr(ci_upper, 'tolist') else list(ci_upper)
                                        
                                        print(f"DEBUG: Adding CI for response={i} ({response_var_name}), shock={j} ({shock_var_name}), CI shape: {irf_ci_lower.shape}")
                                        
                                        # Add upper CI band
                                        fig.add_trace(
                                            go.Scatter(
                                                x=periods,
                                                y=ci_upper_list,
                                                mode='lines',
                                                name='95% CI Upper',
                                                line=dict(width=0),
                                                showlegend=(row_idx == 1 and j == 0),  # Only show legend once
                                                hoverinfo='skip'
                                            ),
                                            row=row_idx, col=1
                                        )
                                        
                                        # Add lower CI band with fill
                                        fig.add_trace(
                                            go.Scatter(
                                                x=periods,
                                                y=ci_lower_list,
                                                mode='lines',
                                                name='95% CI',
                                                line=dict(width=0),
                                                fill='tonexty',
                                                fillcolor='rgba(0, 100, 255, 0.2)',
                                                showlegend=False,
                                                hoverinfo='skip'
                                            ),
                                            row=row_idx, col=1
                                        )
                            except (IndexError, TypeError) as e:
                                print(f"Warning: Could not access irf[:, {i}, {j}], shape: {irf_array.shape}, error: {e}")
                                continue
        else:
            # Unexpected shape - try to handle gracefully
            print(f"Warning: Unexpected IRF shape: {irf_array.shape}")
            return JsonResponse({'success': False, 'error': f'Unexpected IRF array shape: {irf_array.shape}'}, status=400)
        
        # Add zero line for each subplot (for 3D case)
        if len(irf_array.shape) == 3:
            for row_idx in range(1, n_response_vars + 1):
                fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=row_idx, col=1)
            
            # Update y-axis labels
            for row_idx in range(1, n_response_vars + 1):
                fig.update_yaxes(title_text="Response", row=row_idx, col=1)
        
        # Update x-axis label for bottom subplot
        fig.update_xaxes(title_text="Periods", row=n_response_vars, col=1)
        
        # Update layout
        shock_type_label = "Orthogonal" if shock_type == 'orthogonal' else "Generalized (Pesaran-Shin)"
        
        # Calculate appropriate Y-axis range to include CI bands if shown
        if show_ci and irf_ci_lower is not None and irf_ci_upper is not None:
            # Find the min and max across all CI bounds and IRF values
            import numpy as np
            irf_array = np.asarray(irf)
            ci_lower_array = np.asarray(irf_ci_lower)
            ci_upper_array = np.asarray(irf_ci_upper)
            
            # Get overall min and max
            all_min = min(float(np.nanmin(irf_array)), float(np.nanmin(ci_lower_array)))
            all_max = max(float(np.nanmax(irf_array)), float(np.nanmax(ci_upper_array)))
            
            # Add padding (10% on each side)
            y_range = all_max - all_min
            y_padding = y_range * 0.1 if y_range > 0 else 0.1
            y_min = all_min - y_padding
            y_max = all_max + y_padding
            
            # Update Y-axis for all subplots to include CI bands
            for row_idx in range(1, n_response_vars + 1):
                fig.update_yaxes(range=[y_min, y_max], row=row_idx, col=1)
        
        # Increase plot height and adjust margins for better visibility
        fig.update_layout(
            height=400 * n_response_vars,  # Increased from 300 to 400
            showlegend=True,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title_text=f"Impulse Response Functions ({shock_type_label})",
            title_x=0.5,
            margin=dict(l=60, r=40, t=80, b=60),  # Add more margins for better spacing
            autosize=True
        )
        
        # Convert to dict for JSON response
        plot_data = fig.to_dict()
        
        return JsonResponse({
            'success': True,
            'plot_data': plot_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_varx_irf_data_view(request, session_id):
    """Export VARX IRF data as CSV"""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    try:
        session = get_object_or_404(AnalysisSession, pk=session_id)
        
        # Parse JSON body
        import json
        data = json.loads(request.body)
        
        irf_horizon = int(data.get('irf_horizon', 10))
        response_var = data.get('response_var', None)
        shock_var = data.get('shock_var', None)
        shock_type = data.get('shock_type', 'orthogonal')
        show_ci = data.get('show_ci', False)
        
        if irf_horizon < 1 or irf_horizon > 50:
            return HttpResponse('IRF horizon must be between 1 and 50', status=400)
        
        # Load stored model results
        if not session.fitted_model:
            return HttpResponse('No fitted model found. Please run VARX analysis first.', status=400)
        
        try:
            import pickle
            model_data = pickle.loads(session.fitted_model)
            model_results = model_data['model_results']
            dependent_vars = model_data['dependent_vars']
        except Exception as e:
            return HttpResponse(f'Failed to load model: {str(e)}', status=400)
        
        # Generate IRF
        try:
            # VAR uses irf() method, not impulse_responses()
            irf_obj = model_results.irf(irf_horizon)
            
            if shock_type == 'orthogonal':
                # Orthogonalized IRF
                irf = irf_obj.orth_irfs
            else:
                # Generalized IRF (Pesaran-Shin)
                irf = irf_obj.irfs
            
            # If specific shock_var is selected, filter to that shock
            if shock_var and shock_var in dependent_vars:
                shock_idx = dependent_vars.index(shock_var)
                irf = irf[:, :, shock_idx]
            
            # If specific response_var is selected, filter to that response
            if response_var and response_var in dependent_vars:
                response_idx = dependent_vars.index(response_var)
                if len(irf.shape) == 3:
                    irf = irf[:, response_idx, :]
                elif len(irf.shape) == 2:
                    irf = irf[:, response_idx:response_idx+1]
            
            # Calculate CI if requested
            irf_ci_lower = None
            irf_ci_upper = None
            if show_ci:
                try:
                    import scipy.stats as stats
                    import numpy as np
                    import pandas as pd
                    
                    # Try to get standard errors from IRF object
                    irf_stderr = None
                    
                    if hasattr(irf_obj, 'stderr_orth_irfs') and shock_type == 'orthogonal':
                        try:
                            irf_stderr = irf_obj.stderr_orth_irfs
                        except:
                            pass
                    elif hasattr(irf_obj, 'stderr_irfs') and shock_type != 'orthogonal':
                        try:
                            irf_stderr = irf_obj.stderr_irfs
                        except:
                            pass
                    
                    # If standard errors not available, use approximation
                    if irf_stderr is None:
                        param_std = model_results.bse
                        if isinstance(param_std, (pd.DataFrame, pd.Series)):
                            avg_std = float(param_std.values.mean()) if len(param_std) > 0 else 0.1
                        else:
                            avg_std = float(np.mean(param_std)) if len(param_std) > 0 else 0.1
                        
                        irf_array_temp = np.asarray(irf)
                        std_approx = avg_std * np.sqrt(np.arange(irf_horizon + 1) + 1)
                        
                        if len(irf_array_temp.shape) == 2:
                            irf_stderr = std_approx[:, np.newaxis]
                        elif len(irf_array_temp.shape) == 3:
                            irf_stderr = std_approx[:, np.newaxis, np.newaxis]
                        else:
                            irf_stderr = std_approx
                    
                    # Apply same filtering as IRF
                    if irf_stderr is not None:
                        if shock_var and shock_var in dependent_vars:
                            shock_idx = dependent_vars.index(shock_var)
                            if len(irf_stderr.shape) == 3:
                                irf_stderr = irf_stderr[:, :, shock_idx]
                        if response_var and response_var in dependent_vars:
                            response_idx = dependent_vars.index(response_var)
                            if len(irf_stderr.shape) == 3:
                                irf_stderr = irf_stderr[:, response_idx, :]
                            elif len(irf_stderr.shape) == 2:
                                irf_stderr = irf_stderr[:, response_idx:response_idx+1]
                        
                        z_critical = stats.norm.ppf(0.975)
                        irf_array_temp = np.asarray(irf)
                        irf_stderr_array = np.asarray(irf_stderr)
                        
                        # Ensure shapes match
                        if irf_array_temp.shape != irf_stderr_array.shape:
                            try:
                                irf_stderr_array = np.broadcast_to(irf_stderr_array, irf_array_temp.shape).copy()
                            except:
                                irf_stderr = None
                        
                        if irf_stderr is not None:
                            irf_ci_lower = irf_array_temp - z_critical * irf_stderr_array
                            irf_ci_upper = irf_array_temp + z_critical * irf_stderr_array
                except Exception as e:
                    print(f"Warning: Could not calculate CI for IRF: {e}")
                    pass
            
        except Exception as e:
            return HttpResponse(f'Failed to generate IRF: {str(e)}', status=400)
        
        # Convert IRF to CSV format
        import numpy as np
        from io import StringIO
        
        irf_array = np.asarray(irf)
        periods = list(range(irf_horizon + 1))
        
        # Build CSV data
        csv_rows = []
        
        if len(irf_array.shape) == 2:
            # 2D case: (steps+1, n_vars)
            # Columns: Period, Response_Var, IRF_Value, CI_Lower (if available), CI_Upper (if available)
            headers = ['Period']
            for i, var in enumerate(dependent_vars):
                headers.append(f'{var}_IRF')
                if show_ci and irf_ci_lower is not None:
                    headers.append(f'{var}_CI_Lower')
                    headers.append(f'{var}_CI_Upper')
            
            csv_rows.append(','.join(headers))
            
            for period_idx, period in enumerate(periods):
                row = [str(period)]
                for i, var in enumerate(dependent_vars):
                    if i < irf_array.shape[1]:
                        row.append(str(irf_array[period_idx, i]))
                        if show_ci and irf_ci_lower is not None:
                            row.append(str(irf_ci_lower[period_idx, i]))
                            row.append(str(irf_ci_upper[period_idx, i]))
                csv_rows.append(','.join(row))
        
        else:
            # 3D case: (steps+1, n_vars, n_vars)
            # Columns: Period, Response_Var, Shock_Var, IRF_Value, CI_Lower (if available), CI_Upper (if available)
            headers = ['Period', 'Response_Variable', 'Shock_Variable', 'IRF_Value']
            if show_ci and irf_ci_lower is not None:
                headers.extend(['CI_Lower', 'CI_Upper'])
            
            csv_rows.append(','.join(headers))
            
            for period_idx, period in enumerate(periods):
                for i, response_var_name in enumerate(dependent_vars):
                    for j, shock_var_name in enumerate(dependent_vars):
                        if i < irf_array.shape[1] and j < irf_array.shape[2]:
                            row = [
                                str(period),
                                response_var_name,
                                shock_var_name,
                                str(irf_array[period_idx, i, j])
                            ]
                            if show_ci and irf_ci_lower is not None:
                                row.append(str(irf_ci_lower[period_idx, i, j]))
                                row.append(str(irf_ci_upper[period_idx, i, j]))
                            csv_rows.append(','.join(row))
        
        csv_content = '\n'.join(csv_rows)
        
        # Return CSV file
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="varx_irf_data_{session_id}.csv"'
        return response
        
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error: {str(e)}', status=500)


def download_session_history_view(request, session_id):
    """Download session history as text or JSON file."""
    try:
        # Get format parameter (default to 'text')
        format_type = request.GET.get('format', 'text')
        
        # Validate format
        if format_type not in ['text', 'json']:
            format_type = 'text'
        
        # Generate and return the history file
        return download_session_history(session_id, format_type)
        
    except Exception as e:
        return HttpResponse(f"Error generating history: {str(e)}", status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ai_chat(request):
    """
    Handle AI chat requests. Sends user messages to an AI API and returns responses.
    Expects JSON with:
    - message: user's message
    - context (optional): additional context about the current analysis/session
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get API configuration from environment variables
        api_key = os.environ.get('OPENAI_API_KEY', '')
        api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')
        model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Build system prompt with context about Generative Research Assistant
        system_prompt = """You are a helpful AI assistant for Generative Research Assistant, a statistical analysis platform. 
You help users understand their statistical analyses, interpret results, and guide them through the analysis process.
Be concise, accurate, and focus on statistical concepts and interpretations."""
        
        if context:
            context_text = "\nContext about the current analysis:\n"
            if context.get('session_name'):
                context_text += f"Session: {context['session_name']}\n"
            if context.get('formula'):
                context_text += f"Formula: {context['formula']}\n"
            if context.get('module'):
                context_text += f"Analysis Type: {context['module']}\n"
            if context.get('dataset_name'):
                context_text += f"Dataset: {context['dataset_name']}\n"
            system_prompt += context_text
        
        # Prepare messages for the API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # If no API key is configured, return a helpful error message
        if not api_key:
            return JsonResponse({
                'error': 'AI API is not configured. Please set OPENAI_API_KEY environment variable.',
                'response': 'To enable AI chat, configure the OPENAI_API_KEY environment variable in your settings.'
            }, status=503)
        
        # Make request to OpenAI API (or compatible API)
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        try:
            response = requests.post(
                f'{api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not ai_response:
                return JsonResponse({'error': 'No response from AI API'}, status=500)
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'usage': result.get('usage', {})
            })
            
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'error': f'Error communicating with AI API: {str(e)}'
            }, status=502)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


def add_model_errors_to_dataset(request, session_id):
    """Add model residuals/errors to the dataset as new columns"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        import json
        import pickle
        import pandas as pd
        import numpy as np
        from statsmodels.miscmodels.ordinal_model import OrderedModel
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        
        # Get session and dataset
        session = get_object_or_404(AnalysisSession, pk=session_id)
        data = json.loads(request.body)
        dataset_id = data.get('dataset_id')
        
        if not dataset_id:
            return JsonResponse({'error': 'dataset_id is required'}, status=400)
        
        dataset = get_object_or_404(Dataset, pk=dataset_id)
        
        # Check if session has a fitted model
        if not session.fitted_model:
            return JsonResponse({'error': 'No fitted model found for this session'}, status=400)
        
        # Unpickle the fitted model
        try:
            fitted_model = pickle.loads(session.fitted_model)
        except Exception as e:
            return JsonResponse({'error': f'Failed to load fitted model: {str(e)}'}, status=500)
        
        # Load the dataset
        df, column_types, schema_orders = _read_dataset_file(dataset.file_path)
        original_shape = df.shape
        
        # Determine regression type from model
        model_type_str = str(type(fitted_model))
        # Check if model has a .model attribute (for OrderedModel, etc.)
        if hasattr(fitted_model, 'model'):
            model_type_str += ' ' + str(type(fitted_model.model))
        
        print(f"DEBUG: Model type string: {model_type_str}")
        
        # Determine model type name for column naming (with "regression" suffix)
        if 'OrderedModel' in model_type_str:
            model_type_name = 'ordinal_regression'
        elif 'MultinomialResults' in model_type_str:
            model_type_name = 'multinomial_regression'
        elif 'GLMResults' in model_type_str:
            # Check if it's a binomial GLM (logistic regression)
            try:
                if hasattr(fitted_model, 'model') and hasattr(fitted_model.model, 'family'):
                    family_name = str(fitted_model.model.family).lower()
                    if 'binomial' in family_name:
                        model_type_name = 'binomial_regression'
                    else:
                        model_type_name = 'glm_regression'
                else:
                    model_type_name = 'glm_regression'
            except Exception as e:
                print(f"DEBUG: Could not determine GLM family: {e}")
                model_type_name = 'glm_regression'
        elif 'OLSResults' in model_type_str or 'RegressionResults' in model_type_str:
            model_type_name = 'ols_regression'
        else:
            model_type_name = 'model_regression'
        
        print(f"DEBUG: Model type name: {model_type_name}")
        
        # Get session name for column naming
        session_name = session.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        # Remove any special characters that might cause issues
        import re
        session_name = re.sub(r'[^\w\-_]', '_', session_name)
        
        # Prepare to collect residual columns
        residual_columns = {}
        column_names = []
        
        # Calculate residuals based on model type
        if 'OLSResults' in model_type_str or 'RegressionResults' in model_type_str:
            # OLS (Linear Regression)
            # Raw residuals
            residuals = fitted_model.resid
            col_name = f'{session_name}_{model_type_name}_error_raw'
            residual_columns[col_name] = residuals
            column_names.append(col_name)
            
            # Standardized residuals
            if hasattr(fitted_model, 'resid_pearson'):
                pearson_residuals = fitted_model.resid_pearson
                col_name = f'{session_name}_{model_type_name}_error_pearson'
                residual_columns[col_name] = pearson_residuals
                column_names.append(col_name)
        
        elif 'GLMResults' in model_type_str:
            # GLM (Binomial logistic regression or other GLM)
            # Response residuals
            if hasattr(fitted_model, 'resid_response'):
                response_residuals = fitted_model.resid_response
                col_name = f'{session_name}_{model_type_name}_error_response'
                residual_columns[col_name] = response_residuals
                column_names.append(col_name)
            
            # Pearson residuals
            if hasattr(fitted_model, 'resid_pearson'):
                pearson_residuals = fitted_model.resid_pearson
                col_name = f'{session_name}_{model_type_name}_error_pearson'
                residual_columns[col_name] = pearson_residuals
                column_names.append(col_name)
            
            # Deviance residuals
            if hasattr(fitted_model, 'resid_deviance'):
                deviance_residuals = fitted_model.resid_deviance
                col_name = f'{session_name}_{model_type_name}_error_deviance'
                residual_columns[col_name] = deviance_residuals
                column_names.append(col_name)
            
            # Working residuals
            if hasattr(fitted_model, 'resid_working'):
                working_residuals = fitted_model.resid_working
                col_name = f'{session_name}_{model_type_name}_error_working'
                residual_columns[col_name] = working_residuals
                column_names.append(col_name)
        
        elif 'MultinomialResults' in model_type_str:
            # Multinomial Logit
            # Get category names from dependent variable
            category_names = None
            try:
                formula = session.formula
                if '~' in formula:
                    dv = formula.split('~')[0].strip()
                    if dv in df.columns:
                        # Get unique categories from the dependent variable
                        unique_cats = df[dv].dropna().unique()
                        # Sort to ensure consistent ordering (should match model's category order)
                        category_names = sorted([str(cat) for cat in unique_cats])
                        # Sanitize category names for column names
                        category_names = [str(cat).replace(' ', '_').replace('/', '_').replace('\\', '_') for cat in category_names]
                        # Remove any other problematic characters
                        import re
                        category_names = [re.sub(r'[^\w\-_]', '_', cat) for cat in category_names]
                        print(f"DEBUG: Found {len(category_names)} categories: {category_names}")
            except Exception as e:
                print(f"DEBUG: Could not get category names: {e}")
            
            # For multinomial models, resid_response may fail due to shape mismatch
            # Try to calculate response residuals manually if needed
            try:
                if hasattr(fitted_model, 'resid_response'):
                    response_residuals = fitted_model.resid_response
                    print(f"DEBUG: Multinomial resid_response type: {type(response_residuals)}, shape: {getattr(response_residuals, 'shape', 'no shape')}")
                    
                    # resid_response for multinomial is a DataFrame
                    if isinstance(response_residuals, pd.DataFrame):
                        for col in response_residuals.columns:
                            # Extract the column as a Series, ensuring it's 1D
                            residual_series = response_residuals[col]
                            if isinstance(residual_series, pd.Series):
                                # Ensure it's a 1D series
                                if len(residual_series.shape) == 1:
                                    col_name = f'{session_name}_{model_type_name}_error_response_{col}'
                                    residual_columns[col_name] = residual_series
                                    column_names.append(col_name)
                                else:
                                    print(f"DEBUG: Warning - column {col} has shape {residual_series.shape}, skipping")
                            else:
                                # Convert to Series
                                residual_series = pd.Series(residual_series)
                                col_name = f'{session_name}_{model_type_name}_error_response_{col}'
                                residual_columns[col_name] = residual_series
                                column_names.append(col_name)
                    elif isinstance(response_residuals, np.ndarray):
                        # Handle numpy array case
                        if len(response_residuals.shape) == 2:
                            # 2D array - extract each column
                            for col_idx in range(response_residuals.shape[1]):
                                # Use category name if available, otherwise use index
                                if category_names and col_idx < len(category_names):
                                    category_name = category_names[col_idx]
                                else:
                                    category_name = f'cat{col_idx}'
                                col_name = f'{session_name}_{model_type_name}_error_response_{category_name}'
                                residual_columns[col_name] = pd.Series(response_residuals[:, col_idx])
                                column_names.append(col_name)
                        else:
                            # 1D array
                            col_name = f'{session_name}_{model_type_name}_error_response'
                            residual_columns[col_name] = pd.Series(response_residuals)
                            column_names.append(col_name)
                    else:
                        # Try to convert to Series
                        try:
                            residual_series = pd.Series(response_residuals)
                            col_name = f'{session_name}_{model_type_name}_error_response'
                            residual_columns[col_name] = residual_series
                            column_names.append(col_name)
                        except Exception as e:
                            print(f"DEBUG: Error converting resid_response to Series: {e}")
            except (ValueError, AttributeError) as e:
                # resid_response fails for multinomial models due to shape mismatch
                # Calculate it manually: convert actual values to one-hot and subtract predictions
                print(f"DEBUG: resid_response not available for multinomial model: {e}")
                print(f"DEBUG: Calculating response residuals manually...")
                try:
                    # Get predictions (probabilities for each category)
                    predictions = fitted_model.predict()  # Shape: (n_samples, n_categories)
                    # Get actual values (category indices)
                    actual_values = fitted_model.model.endog  # Shape: (n_samples,)
                    
                    # Convert actual values to one-hot encoding
                    n_categories = predictions.shape[1]
                    actual_onehot = np.zeros_like(predictions)
                    for i, actual_cat in enumerate(actual_values):
                        if not np.isnan(actual_cat) and 0 <= int(actual_cat) < n_categories:
                            actual_onehot[i, int(actual_cat)] = 1.0
                    
                    # Calculate response residuals: actual_onehot - predictions
                    response_residuals = actual_onehot - predictions
                    
                    # Add each category's residuals as a separate column
                    for col_idx in range(response_residuals.shape[1]):
                        # Use category name if available, otherwise use index
                        if category_names and col_idx < len(category_names):
                            category_name = category_names[col_idx]
                        else:
                            category_name = f'cat{col_idx}'
                        col_name = f'{session_name}_{model_type_name}_error_response_{category_name}'
                        residual_columns[col_name] = pd.Series(response_residuals[:, col_idx])
                        column_names.append(col_name)
                    print(f"DEBUG: Successfully calculated {response_residuals.shape[1]} response residual columns")
                except Exception as e2:
                    print(f"DEBUG: Failed to calculate response residuals manually: {e2}")
            
            # Pearson residuals - these should work better for multinomial
            try:
                if hasattr(fitted_model, 'resid_pearson'):
                    pearson_residuals = fitted_model.resid_pearson
                    print(f"DEBUG: Multinomial resid_pearson type: {type(pearson_residuals)}, shape: {getattr(pearson_residuals, 'shape', 'no shape')}")
                    
                    if isinstance(pearson_residuals, pd.DataFrame):
                        for col in pearson_residuals.columns:
                            # Extract the column as a Series, ensuring it's 1D
                            residual_series = pearson_residuals[col]
                            if isinstance(residual_series, pd.Series):
                                if len(residual_series.shape) == 1:
                                    col_name = f'{session_name}_{model_type_name}_error_pearson_{col}'
                                    residual_columns[col_name] = residual_series
                                    column_names.append(col_name)
                                else:
                                    print(f"DEBUG: Warning - column {col} has shape {residual_series.shape}, skipping")
                            else:
                                residual_series = pd.Series(residual_series)
                                col_name = f'{session_name}_{model_type_name}_error_pearson_{col}'
                                residual_columns[col_name] = residual_series
                                column_names.append(col_name)
                    elif isinstance(pearson_residuals, np.ndarray):
                        # Handle numpy array case
                        if len(pearson_residuals.shape) == 2:
                            # 2D array - extract each column
                            for col_idx in range(pearson_residuals.shape[1]):
                                # Use category name if available, otherwise use index
                                if category_names and col_idx < len(category_names):
                                    category_name = category_names[col_idx]
                                else:
                                    category_name = f'cat{col_idx}'
                                col_name = f'{session_name}_{model_type_name}_error_pearson_{category_name}'
                                residual_columns[col_name] = pd.Series(pearson_residuals[:, col_idx])
                                column_names.append(col_name)
                        else:
                            # 1D array
                            col_name = f'{session_name}_{model_type_name}_error_pearson'
                            residual_columns[col_name] = pd.Series(pearson_residuals)
                            column_names.append(col_name)
                    else:
                        # Try to convert to Series
                        try:
                            residual_series = pd.Series(pearson_residuals)
                            col_name = f'{session_name}_{model_type_name}_error_pearson'
                            residual_columns[col_name] = residual_series
                            column_names.append(col_name)
                        except Exception as e:
                            print(f"DEBUG: Error converting resid_pearson to Series: {e}")
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: resid_pearson not available for multinomial model: {e}")
        
        elif 'OrderedModel' in model_type_str:
            # Ordered Logit / Probit
            # For OrderedModel, we need to calculate residuals manually
            # Get the dependent variable from the formula
            formula = session.formula
            if '~' in formula:
                dv = formula.split('~')[0].strip()
                
                # Get predictions
                if hasattr(fitted_model, 'predict'):
                    try:
                        predictions = fitted_model.predict()
                        print(f"DEBUG: OrderedModel predictions shape: {predictions.shape if hasattr(predictions, 'shape') else 'no shape'}")
                        print(f"DEBUG: OrderedModel predictions type: {type(predictions)}")
                        
                        # For ordinal models, predictions are typically a 2D array (n_samples x n_classes)
                        if isinstance(predictions, np.ndarray):
                            if len(predictions.shape) > 1:
                                # For 2D array, use predicted probability for a specific class
                                # Typically use the probability of the most likely class or a middle class
                                if predictions.shape[1] > 1:
                                    # Use the mean probability or the probability of the most common class
                                    # Or use probability of the second class as in the example
                                    predicted_prob = predictions[:, 1]  # Probability for second class
                                else:
                                    predicted_prob = predictions[:, 0]
                            else:
                                # 1D array
                                predicted_prob = predictions
                        elif isinstance(predictions, pd.DataFrame):
                            # DataFrame with columns for each class
                            if predictions.shape[1] > 1:
                                predicted_prob = predictions.iloc[:, 1].values
                            else:
                                predicted_prob = predictions.iloc[:, 0].values
                        else:
                            # Try to convert to array
                            predictions_array = np.array(predictions)
                            if len(predictions_array.shape) > 1 and predictions_array.shape[1] > 1:
                                predicted_prob = predictions_array[:, 1]
                            else:
                                predicted_prob = predictions_array.flatten()
                        
                        # Get actual values - need to match the data used in model fitting
                        # The model was fitted on cleaned data, so we need to get the same subset
                        if dv in df.columns:
                            # Load the data again the same way the model was fitted
                            # For now, use all values and let alignment handle the mismatch
                            actual_values_full = df[dv].copy()
                            
                            # If actual values are categorical, convert to numeric codes
                            if not pd.api.types.is_numeric_dtype(actual_values_full):
                                actual_values_full = pd.Categorical(actual_values_full).codes
                                actual_values_full = pd.Series(actual_values_full, index=df.index).replace(-1, np.nan)
                            
                            # The predictions correspond to the cleaned data (after dropping NaN)
                            # So we need to align them properly
                            # Create a series with the same length as predictions
                            actual_values_clean = actual_values_full.dropna()
                            
                            # Calculate response residuals for the clean data
                            if len(actual_values_clean) == len(predicted_prob):
                                response_residuals_clean = actual_values_clean.values - predicted_prob
                                # Create a full-length series with NaN for missing values
                                response_residuals = pd.Series(index=df.index, dtype=float)
                                response_residuals.loc[actual_values_clean.index] = response_residuals_clean
                                response_residuals.loc[actual_values_full.isna()] = np.nan
                                
                                col_name = f'{session_name}_{model_type_name}_error'
                                residual_columns[col_name] = response_residuals
                                column_names.append(col_name)
                                print(f"DEBUG: Added {col_name} with {len(response_residuals.dropna())} non-null values")
                            else:
                                print(f"DEBUG: Length mismatch - actual: {len(actual_values_clean)}, predicted: {len(predicted_prob)}")
                                # Fallback: try to align by index
                                response_residuals = pd.Series(index=df.index, dtype=float)
                                min_len = min(len(actual_values_clean), len(predicted_prob))
                                response_residuals.iloc[:min_len] = actual_values_clean.iloc[:min_len].values - predicted_prob[:min_len]
                                col_name = f'{session_name}_{model_type_name}_error'
                                residual_columns[col_name] = response_residuals
                                column_names.append(col_name)
                    except Exception as e:
                        import traceback
                        print(f"Error calculating ordered model residuals: {e}")
                        print(traceback.format_exc())
                        # Don't add anything if there's an error
                        pass
        else:
            # Fallback: Try to get residuals from common attributes
            print(f"DEBUG: Unknown model type: {model_type_str}")
            print(f"DEBUG: Trying fallback residual extraction...")
            
            # Try to get any available residual attribute
            residual_attrs = ['resid', 'resid_response', 'resid_pearson', 'resid_deviance', 'resid_working']
            found_any = False
            
            for attr in residual_attrs:
                if hasattr(fitted_model, attr):
                    try:
                        residuals = getattr(fitted_model, attr)
                        if attr == 'resid':
                            base_name = 'error'
                        else:
                            # Convert resid_response -> error_response, resid_pearson -> error_pearson, etc.
                            base_name = attr.replace('resid', 'error')
                        
                        col_name = f'{session_name}_{model_type_name}_{base_name}'
                        
                        if isinstance(residuals, pd.DataFrame):
                            # Handle DataFrame case (e.g., multinomial)
                            for col in residuals.columns:
                                df_col_name = f'{col_name}_{col}'
                                residual_columns[df_col_name] = residuals[col]
                                column_names.append(df_col_name)
                        else:
                            residual_columns[col_name] = residuals
                            column_names.append(col_name)
                        found_any = True
                        print(f"DEBUG: Found and added {attr} as {col_name}")
                    except Exception as e:
                        print(f"DEBUG: Error accessing {attr}: {e}")
                        continue
            
            if not found_any:
                print(f"DEBUG: No residual attributes found. Model attributes: {[a for a in dir(fitted_model) if 'resid' in a.lower()]}")
        
        # Add residual columns to dataframe
        # Align indices - residuals might have different index due to dropped rows
        for col_name, residuals in residual_columns.items():
            try:
                if isinstance(residuals, pd.DataFrame):
                    # For DataFrame residuals (e.g., multinomial with multiple categories)
                    # Each column should be added separately (shouldn't happen here as we already split them)
                    # But handle it just in case
                    for col in residuals.columns:
                        df_col_name = f'{col_name}_{col}'
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals) <= len(df):
                            aligned_residuals.iloc[:len(residuals)] = residuals[col].values
                            aligned_residuals.iloc[len(residuals):] = np.nan
                        else:
                            aligned_residuals = residuals[col].iloc[:len(df)]
                        df[df_col_name] = aligned_residuals
                elif isinstance(residuals, pd.Series):
                    # Create a new series with the same index as df
                    aligned_residuals = pd.Series(index=df.index, dtype=float)
                    # Map residuals to original indices (residuals use cleaned data indices)
                    # We need to align them properly - residuals typically use the cleaned data index
                    # For now, try to align by position if indices don't match
                    if len(residuals) <= len(df):
                        # If residuals are shorter, pad with NaN
                        aligned_residuals.iloc[:len(residuals)] = residuals.values
                        aligned_residuals.iloc[len(residuals):] = np.nan
                    else:
                        # If residuals are longer, truncate (shouldn't happen)
                        aligned_residuals = residuals.iloc[:len(df)]
                    
                    df[col_name] = aligned_residuals
                elif isinstance(residuals, np.ndarray):
                    # Handle numpy arrays
                    if len(residuals.shape) == 1:
                        # 1D array
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals) <= len(df):
                            aligned_residuals.iloc[:len(residuals)] = residuals
                            aligned_residuals.iloc[len(residuals):] = np.nan
                        else:
                            aligned_residuals = pd.Series(residuals[:len(df)], index=df.index)
                        df[col_name] = aligned_residuals
                    else:
                        # Multi-dimensional array - this shouldn't happen for single column
                        print(f"DEBUG: Warning - residuals for {col_name} is {residuals.shape}D array, skipping")
                        continue
                else:
                    # Convert to Series if not already
                    residuals_array = np.array(residuals)
                    if len(residuals_array.shape) == 1:
                        aligned_residuals = pd.Series(index=df.index, dtype=float)
                        if len(residuals_array) <= len(df):
                            aligned_residuals.iloc[:len(residuals_array)] = residuals_array
                            aligned_residuals.iloc[len(residuals_array):] = np.nan
                        else:
                            aligned_residuals = pd.Series(residuals_array[:len(df)], index=df.index)
                        df[col_name] = aligned_residuals
                    else:
                        print(f"DEBUG: Warning - residuals for {col_name} has shape {residuals_array.shape}, skipping")
                        continue
            except Exception as e:
                print(f"DEBUG: Error adding column {col_name}: {e}")
                import traceback
                print(traceback.format_exc())
                continue
        
        # Save the updated dataset
        file_path = dataset.file_path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        def _write_dataframe(out_path, fmt):
            if fmt in ('.csv', ''):
                df.to_csv(out_path, index=False)
            elif fmt == '.xlsx':
                df.to_excel(out_path, index=False)
            elif fmt == '.xls':
                df.to_excel(out_path, index=False)
            elif fmt == '.tsv':
                df.to_csv(out_path, sep='\t', index=False)
            elif fmt == '.json':
                df.to_json(out_path, orient='records', indent=2)
            else:
                df.to_csv(out_path, index=False)
        
        _write_dataframe(file_path, file_ext)
        
        return JsonResponse({
            'success': True,
            'columns_added': len(column_names),
            'column_names': column_names,
            'message': f'Successfully added {len(column_names)} residual column(s) to dataset'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}\nTraceback: {traceback.format_exc()}'
        print(error_msg)
        return JsonResponse({'error': f'Failed to add model errors: {str(e)}'}, status=500)
