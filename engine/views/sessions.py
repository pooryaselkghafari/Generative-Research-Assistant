"""
Views for session management (list, edit, delete).
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from engine.models import AnalysisSession, Dataset, Paper
from engine.modules import get_registry
from history.history import download_session_history
import os
import shutil


def _list_context(current_session=None, user=None):
    """
    Get context for listing sessions and datasets.
    Only shows data for the specified user (security: user isolation).
    """
    if user is None or not user.is_authenticated:
        # Return empty context for unauthenticated users
        registry = get_registry()
        return {
            'sessions': AnalysisSession.objects.none(),
            'datasets': Dataset.objects.none(),
            'modules': registry,
            'current': current_session,
            'line_styles': ['solid', 'dashed', 'dotted', 'dashdot'],
        }
    
    # Filter by user - only show user's own data
    sessions = AnalysisSession.objects.filter(user=user).order_by('-updated_at')[:50]
    datasets = Dataset.objects.filter(user=user).order_by('-uploaded_at')
    papers = Paper.objects.filter(user=user).order_by('-updated_at')
    
    # Group sessions by paper
    sessions_by_paper = {}
    ungrouped_sessions = []
    
    for session in sessions:
        if session.paper:
            paper_id = session.paper.id
            if paper_id not in sessions_by_paper:
                sessions_by_paper[paper_id] = {
                    'paper': session.paper,
                    'sessions': []
                }
            sessions_by_paper[paper_id]['sessions'].append(session)
        else:
            ungrouped_sessions.append(session)
    
    # Convert to list for template
    papers_with_sessions = []
    for paper in papers:
        if paper.id in sessions_by_paper:
            papers_with_sessions.append(sessions_by_paper[paper.id])
        else:
            # Paper exists but has no sessions yet
            papers_with_sessions.append({
                'paper': paper,
                'sessions': []
            })
    
    registry = get_registry()
    return {
        'sessions': sessions,
        'ungrouped_sessions': ungrouped_sessions,
        'papers_with_sessions': papers_with_sessions,
        'datasets': datasets,
        'papers': papers,
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
            # Security: Only allow access to user's own sessions
            session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
            context = _list_context(current_session=session, user=request.user)
        except (ValueError, AnalysisSession.DoesNotExist):
            # Invalid session_id or not owned by user, just use default context
            context = _list_context(user=request.user)
    else:
        context = _list_context(user=request.user)
    
    # Check if a specific dataset should be auto-selected
    dataset_id = request.GET.get('dataset_id')
    if dataset_id:
        # Security: Verify dataset belongs to user
        try:
            Dataset.objects.get(pk=dataset_id, user=request.user)
            context['auto_select_dataset_id'] = dataset_id
        except Dataset.DoesNotExist:
            # Dataset doesn't exist or doesn't belong to user - ignore
            pass
    
    return render(request, 'engine/index.html', context)


def edit_session(request, pk: int):
    # Require authentication
    if not request.user.is_authenticated:
        return redirect('login')
    # Security: Only allow access to user's own sessions
    s = get_object_or_404(AnalysisSession, pk=pk, user=request.user)
    return render(request, 'engine/index.html', _list_context(current_session=s, user=request.user))


def delete_session(request, pk: int):
    # Require authentication
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)

    # Security: Only allow deletion of user's own sessions
    s = get_object_or_404(AnalysisSession, pk=pk, user=request.user)

    # Best-effort cleanup of this session's output folder(s) under MEDIA_ROOT
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
    # Require authentication
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    session_ids = request.POST.getlist('session_ids')
    if not session_ids:
        return redirect('index')
    
    # Security: Only allow deletion of user's own sessions
    sessions_to_delete = AnalysisSession.objects.filter(id__in=session_ids, user=request.user)
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


def download_session_history_view(request, session_id):
    """Download session history as text or JSON file."""
    # Require authentication
    if not request.user.is_authenticated:
        return HttpResponse('Authentication required', status=401)
    try:
        # Get format parameter (default to 'text')
        format_type = request.GET.get('format', 'text')
        
        # Validate format
        if format_type not in ['text', 'json']:
            format_type = 'text'
        
        # Security: Verify session belongs to user before downloading
        session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
        # Generate and return the history file
        return download_session_history(session_id, format_type)
        
    except Exception as e:
        return HttpResponse(f"Error generating history: {str(e)}", status=500)


