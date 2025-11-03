from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json

# Optional Stripe import - only if available
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from engine.models import UserProfile, SubscriptionPlan, Payment

# Initialize Stripe only if available
if STRIPE_AVAILABLE:
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('index')
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        # Handle AJAX requests for modal login
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': f'Welcome back, {user.username}!',
                    'redirect_url': '/app/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid username or password.'
                }, status=400)
        
        # Regular form submission (non-AJAX)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')

@login_required
def profile_view(request):
    profile = request.user.profile
    context = {
        'profile': profile,
        'subscription_plans': SubscriptionPlan.objects.filter(is_active=True),
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def subscription_view(request):
    profile = request.user.profile
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    context = {
        'profile': profile,
        'plans': plans,
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
    }
    return render(request, 'accounts/subscription.html', context)

@login_required
def create_checkout_session(request, plan_id):
    if not STRIPE_AVAILABLE:
        return JsonResponse({'error': 'Stripe not configured. This is a demo mode.'}, status=400)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        profile = request.user.profile
        
        # Create or get Stripe customer
        if not profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.username,
            )
            profile.stripe_customer_id = customer.id
            profile.save()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=profile.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripe_price_id_monthly,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/accounts/subscription/success/'),
            cancel_url=request.build_absolute_uri('/accounts/subscription/'),
        )
        
        return JsonResponse({'checkout_url': checkout_session.url})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def subscription_success(request):
    messages.success(request, 'Subscription activated successfully!')
    return redirect('profile')

@login_required
def cancel_subscription(request):
    try:
        profile = request.user.profile
        if profile.stripe_subscription_id:
            stripe.Subscription.modify(
                profile.stripe_subscription_id,
                cancel_at_period_end=True
            )
            messages.info(request, 'Subscription will be cancelled at the end of the current period.')
        else:
            messages.error(request, 'No active subscription found.')
    except Exception as e:
        messages.error(request, f'Error cancelling subscription: {str(e)}')
    
    return redirect('subscription')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Update user subscription
        handle_successful_payment(session)
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Update subscription status
        handle_subscription_update(subscription)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Handle subscription cancellation
        handle_subscription_cancellation(subscription)
    
    return JsonResponse({'status': 'success'})

def handle_successful_payment(session):
    try:
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        profile = UserProfile.objects.get(stripe_customer_id=customer_id)
        profile.stripe_subscription_id = subscription_id
        profile.subscription_type = 'basic'  # Update based on plan
        profile.subscription_start = timezone.now()
        profile.subscription_end = timezone.now() + timedelta(days=30)
        profile.save()
    except Exception as e:
        print(f"Error handling successful payment: {e}")

def handle_subscription_update(subscription):
    try:
        profile = UserProfile.objects.get(stripe_subscription_id=subscription['id'])
        if subscription['status'] == 'active':
            profile.is_active = True
        else:
            profile.is_active = False
        profile.save()
    except Exception as e:
        print(f"Error handling subscription update: {e}")

def handle_subscription_cancellation(subscription):
    try:
        profile = UserProfile.objects.get(stripe_subscription_id=subscription['id'])
        profile.subscription_type = 'free'
        profile.stripe_subscription_id = None
        profile.is_active = False
        profile.save()
    except Exception as e:
        print(f"Error handling subscription cancellation: {e}")
