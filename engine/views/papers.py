"""
Views for paper management (create, edit, delete, add sessions).
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from engine.models import Paper, AnalysisSession
import json


@login_required
@require_http_methods(["GET"])
def paper_list(request):
    """List all papers for the current user."""
    papers = Paper.objects.filter(user=request.user).order_by('-updated_at')
    
    # Get session counts for each paper
    papers_with_counts = []
    for paper in papers:
        papers_with_counts.append({
            'paper': paper,
            'session_count': paper.get_sessions_count(),
        })
    
    context = {
        'papers': papers_with_counts,
    }
    return render(request, 'engine/papers/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def paper_create(request):
    """Create a new paper."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Paper name is required'}, status=400)
        
        # Check if paper with same name already exists for this user
        if Paper.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'error': 'A paper with this name already exists'}, status=400)
        
        paper = Paper.objects.create(
            user=request.user,
            name=name,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'paper_id': paper.id,
            'paper_name': paper.name,
            'message': 'Paper created successfully'
        })
    
    # GET request - return form (if needed for non-AJAX)
    return render(request, 'engine/papers/create.html')


@login_required
@require_http_methods(["GET", "POST"])
def paper_edit(request, paper_id):
    """Edit an existing paper."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Paper name is required'}, status=400)
        
        # Check if another paper with same name exists
        existing = Paper.objects.filter(user=request.user, name=name).exclude(pk=paper_id)
        if existing.exists():
            return JsonResponse({'error': 'A paper with this name already exists'}, status=400)
        
        paper.name = name
        paper.description = description
        paper.save()
        
        return JsonResponse({
            'success': True,
            'paper_id': paper.id,
            'paper_name': paper.name,
            'message': 'Paper updated successfully'
        })
    
    # GET request
    sessions = paper.get_sessions()
    context = {
        'paper': paper,
        'sessions': sessions,
    }
    return render(request, 'engine/papers/detail.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def paper_delete(request, paper_id):
    """Delete a paper. Sessions are not deleted, just ungrouped."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    
    # Unlink all sessions from this paper (don't delete sessions)
    AnalysisSession.objects.filter(paper=paper, user=request.user).update(paper=None)
    
    paper_name = paper.name
    paper.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Paper "{paper_name}" deleted. Sessions were ungrouped.'
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def paper_add_sessions(request, paper_id):
    """Add one or more sessions to a paper."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        session_ids = data.get('session_ids', [])
        
        if not session_ids:
            return JsonResponse({'error': 'No session IDs provided'}, status=400)
        
        # Verify all sessions belong to the user
        sessions = AnalysisSession.objects.filter(
            pk__in=session_ids,
            user=request.user
        )
        
        if sessions.count() != len(session_ids):
            return JsonResponse({'error': 'Some sessions not found or not accessible'}, status=403)
        
        # Add sessions to paper
        updated_count = sessions.update(paper=paper)
        
        return JsonResponse({
            'success': True,
            'message': f'Added {updated_count} session(s) to paper "{paper.name}"',
            'updated_count': updated_count
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def paper_remove_session(request, paper_id, session_id):
    """Remove a session from a paper."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    session = get_object_or_404(AnalysisSession, pk=session_id, user=request.user)
    
    if session.paper != paper:
        return JsonResponse({'error': 'Session is not in this paper'}, status=400)
    
    session.paper = None
    session.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Session "{session.name}" removed from paper "{paper.name}"'
    })


@login_required
@require_http_methods(["GET"])
def paper_detail_api(request, paper_id):
    """API endpoint to get paper details with sessions."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    
    sessions = paper.get_sessions()
    sessions_data = [{
        'id': s.id,
        'name': s.name,
        'module': s.module,
        'analysis_type': s.analysis_type,
        'updated_at': s.updated_at.isoformat(),
    } for s in sessions]
    
    return JsonResponse({
        'id': paper.id,
        'name': paper.name,
        'description': paper.description,
        'created_at': paper.created_at.isoformat(),
        'updated_at': paper.updated_at.isoformat(),
        'session_count': paper.get_sessions_count(),
        'sessions': sessions_data,
    })


@login_required
@require_http_methods(["GET"])
def paper_list_api(request):
    """API endpoint to list all papers for the current user."""
    papers = Paper.objects.filter(user=request.user).order_by('-updated_at')
    papers_data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'created_at': p.created_at.isoformat(),
        'updated_at': p.updated_at.isoformat(),
        'session_count': p.get_sessions_count(),
    } for p in papers]
    
    return JsonResponse(papers_data, safe=False)


@login_required
@require_http_methods(["GET", "POST"])
@csrf_exempt
def paper_update_keywords_journals(request, paper_id):
    """Update keywords and target journals for a paper."""
    paper = get_object_or_404(Paper, pk=paper_id, user=request.user)
    
    if request.method == 'GET':
        # Return current keywords and journals
        return JsonResponse({
            'success': True,
            'keywords': paper.keywords or [],
            'target_journals': paper.target_journals or [],
        })
    
    # POST - Update keywords and journals
    try:
        data = json.loads(request.body)
        keywords = data.get('keywords', [])
        target_journals = data.get('target_journals', [])
        
        # Validate that keywords and journals are lists
        if not isinstance(keywords, list):
            return JsonResponse({'error': 'Keywords must be a list'}, status=400)
        if not isinstance(target_journals, list):
            return JsonResponse({'error': 'Target journals must be a list'}, status=400)
        
        # Validate list items are strings
        if not all(isinstance(k, str) for k in keywords):
            return JsonResponse({'error': 'All keywords must be strings'}, status=400)
        if not all(isinstance(j, str) for j in target_journals):
            return JsonResponse({'error': 'All journal names must be strings'}, status=400)
        
        # Update paper
        paper.keywords = [k.strip() for k in keywords if k.strip()]
        paper.target_journals = [j.strip() for j in target_journals if j.strip()]
        paper.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Keywords and journals updated successfully',
            'keywords': paper.keywords,
            'target_journals': paper.target_journals,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

