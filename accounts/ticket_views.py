"""
Views for the ticket/bug reporting system.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from engine.models import Ticket


@login_required
def ticket_list(request):
    """
    Display list of tickets for the current user.
    """
    tickets = Ticket.objects.filter(user=request.user)
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tickets': page_obj,
        'status_filter': status_filter,
        'status_choices': Ticket.STATUS_CHOICES,
    }
    return render(request, 'accounts/ticket_list.html', context)


@login_required
def ticket_create(request):
    """
    Create a new ticket.
    """
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', 'medium')
        
        # Validation
        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'accounts/ticket_create.html', {
                'priority_choices': Ticket.PRIORITY_CHOICES,
                'title': title,
                'description': description,
                'priority': priority,
            })
        
        if not description:
            messages.error(request, 'Description is required.')
            return render(request, 'accounts/ticket_create.html', {
                'priority_choices': Ticket.PRIORITY_CHOICES,
                'title': title,
                'description': description,
                'priority': priority,
            })
        
        # Create ticket
        ticket = Ticket.objects.create(
            user=request.user,
            title=title,
            description=description,
            priority=priority,
        )
        
        messages.success(request, f'Ticket #{ticket.id} created successfully. We will review it soon.')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    return render(request, 'accounts/ticket_create.html', {
        'priority_choices': Ticket.PRIORITY_CHOICES,
    })


@login_required
def ticket_detail(request, ticket_id):
    """
    View details of a specific ticket.
    Only the ticket owner can view their tickets.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    context = {
        'ticket': ticket,
    }
    return render(request, 'accounts/ticket_detail.html', context)

