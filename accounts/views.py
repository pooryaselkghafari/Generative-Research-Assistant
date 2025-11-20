from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django import forms
from datetime import timedelta
import json

from .email_service import send_welcome_email, send_verification_email, send_password_reset_email


class UserRegistrationForm(UserCreationForm):
    """Custom registration form that includes email field."""
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

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
    """
    Custom registration view that uses the CustomAccountAdapter for consistency.
    This ensures the same profile creation logic is used as Google sign-in.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create user from form first (but don't save yet)
                user = form.save(commit=False)
                user.email = form.cleaned_data['email']
                
                # Use the adapter to save user (same as allauth does)
                from accounts.adapters import CustomAccountAdapter
                adapter = CustomAccountAdapter()
                
                # Save user using adapter (this will create the profile)
                user = adapter.save_user(request, user, form, commit=True)
                
                # Always require email verification (even with console backend for consistency)
                # Set user as inactive until email is verified
                user.is_active = False
                user.save()
                
                # Send welcome and verification emails
                welcome_sent = False
                verification_sent = False
                
                try:
                    # Try to send welcome email
                    try:
                        welcome_sent = send_welcome_email(user, request)
                        if welcome_sent:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Welcome email sent to {user.email}")
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send welcome email to {user.email}: {e}")
                    
                    # Try to send verification email (more important)
                    try:
                        verification_sent = send_verification_email(user, request)
                        if verification_sent:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Verification email sent to {user.email}")
                    except Exception as e:
                        import logging
                        import traceback
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send verification email to {user.email}: {e}\n{traceback.format_exc()}")
                
                except Exception as e:
                    # If email fails completely, log and continue
                    import logging
                    import traceback
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send registration emails to {user.email}: {e}\n{traceback.format_exc()}")
                
                # Show appropriate message based on email sending results
                if verification_sent:
                    messages.success(request, f'Account created successfully! We\'ve sent a verification email to {user.email}. Please check your inbox (and spam folder) and click the verification link to activate your account.')
                    messages.info(request, 'If you don\'t receive the email within a few minutes, please check your spam folder or contact support.')
                    return redirect('login')
                elif welcome_sent:
                    # Welcome sent but verification failed - still need verification
                    messages.warning(request, f'Account created! We sent a welcome email but had trouble sending the verification email. Your account is inactive until verified. Please contact support to verify your account.')
                    return redirect('login')
                else:
                    # Both emails failed - user must contact support to activate
                    messages.error(request, f'Account created, but we could not send verification emails. Your account is inactive until verified. Please contact support with your email ({user.email}) to activate your account.')
                    return redirect('login')
            except Exception as e:
                # Catch any unexpected errors during registration
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.error(f"Registration error: {e}\n{traceback.format_exc()}")
                messages.error(request, f'An error occurred during registration. Please try again or contact support if the problem persists.')
                # Re-render form with error
                return render(request, 'accounts/register.html', {'form': form})
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        # First check if user exists and is inactive (before authentication)
        # This helps us show a better error message
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            # Try to get user by username or email
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user_obj = User.objects.get(email=username)
            except User.DoesNotExist:
                user_obj = None
        
        # Authenticate user
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
                # Check if user exists but is inactive
                if user_obj is not None and not user_obj.is_active:
                    return JsonResponse({
                        'success': False,
                        'message': 'Your account is not activated. Please check your email for the verification link to activate your account.'
                    }, status=400)
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
            # Check if user exists but is inactive (authentication failed due to inactive status)
            if user_obj is not None and not user_obj.is_active:
                messages.error(request, 'Your account is not activated. Please check your email for the verification link to activate your account.')
            else:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')

@login_required
def profile_view(request):
    """
    Display user profile page.
    
    Handles cases where UserProfile doesn't exist (e.g., Google OAuth users)
    by creating a default profile with safe fallbacks.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get or create user profile (handle case where profile doesn't exist)
        # This is critical for Google OAuth users who might not have profiles
        created = False
        try:
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'subscription_type': 'free',
                    'ai_tier': 'none'
                }
            )
            if created:
                logger.info(f"Created new UserProfile for user {request.user.username}")
        except Exception as e:
            logger.error(f"Error creating/getting UserProfile for user {request.user.username}: {e}", exc_info=True)
            # Try to get existing profile as fallback
            try:
                profile = UserProfile.objects.get(user=request.user)
                created = False
            except UserProfile.DoesNotExist:
                # Last resort: create a minimal profile without get_or_create
                profile = UserProfile.objects.create(
                    user=request.user,
                    subscription_type='free',
                    ai_tier='none'
                )
                created = True
                logger.warning(f"Created UserProfile using fallback method for user {request.user.username}")
        
        # If profile was just created, try to set AI tier from tier settings
        if created:
            try:
                from engine.models import SubscriptionTierSettings
                tier_settings = SubscriptionTierSettings.objects.get(tier='free')
                profile.ai_tier = tier_settings.ai_tier
                profile.save()
            except SubscriptionTierSettings.DoesNotExist:
                logger.warning("SubscriptionTierSettings for 'free' tier not found, using default 'none'")
            except Exception as e:
                logger.warning(f"Error setting AI tier from tier settings: {e}")
        
        # Build context with safe fallbacks
        try:
            from engine.models import Ticket
            open_tickets_count = Ticket.objects.filter(user=request.user, status='open').count()
            total_tickets_count = Ticket.objects.filter(user=request.user).count()
        except Exception as e:
            logger.warning(f"Error fetching ticket counts: {e}")
            open_tickets_count = 0
            total_tickets_count = 0
        
        try:
            subscription_plans = SubscriptionPlan.objects.filter(is_active=True)
        except Exception as e:
            logger.warning(f"Error fetching subscription plans: {e}")
            subscription_plans = []
        
        context = {
            'profile': profile,
            'subscription_plans': subscription_plans,
            'open_tickets_count': open_tickets_count,
            'total_tickets_count': total_tickets_count,
        }
        
        return render(request, 'accounts/profile.html', context)
    
    except Exception as e:
        logger.error(f"Critical error in profile_view for user {request.user.username}: {e}", exc_info=True)
        # Return a minimal error page instead of 500
        messages.error(request, f"An error occurred while loading your profile. Please try again or contact support.")
        return redirect('index')

@login_required
def subscription_view(request):
    # Get or create user profile (handle case where profile doesn't exist)
    # This is critical for Google OAuth users who might not have profiles
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'subscription_type': 'free',
            'ai_tier': 'none'
        }
    )
    
    # If profile was just created, try to set AI tier from tier settings
    if created:
        try:
            from engine.models import SubscriptionTierSettings
            tier_settings = SubscriptionTierSettings.objects.get(tier='free')
            profile.ai_tier = tier_settings.ai_tier
            profile.save()
        except SubscriptionTierSettings.DoesNotExist:
            pass
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    # Update user's AI tier based on subscription type
    from engine.models import SubscriptionTierSettings
    try:
        tier_settings = SubscriptionTierSettings.objects.get(tier=profile.subscription_type)
        if profile.ai_tier != tier_settings.ai_tier:
            profile.ai_tier = tier_settings.ai_tier
            profile.save()
    except SubscriptionTierSettings.DoesNotExist:
        pass
    
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
        # Get or create user profile (handle case where profile doesn't exist)
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'subscription_type': 'free',
                'ai_tier': 'none'
            }
        )
        
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
        # Get or create user profile (handle case where profile doesn't exist)
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'subscription_type': 'free',
                'ai_tier': 'none'
            }
        )
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
        from engine.models import SubscriptionPlan, SubscriptionTierSettings
        from datetime import timedelta
        
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        profile = UserProfile.objects.get(stripe_customer_id=customer_id)
        profile.stripe_subscription_id = subscription_id
        
        # Get the plan from Stripe subscription or line items
        plan = None
        if 'line_items' in session and session['line_items'].get('data'):
            price_id = session['line_items']['data'][0]['price']['id']
            # Find plan by Stripe price ID
            plan = SubscriptionPlan.objects.filter(
                stripe_price_id_monthly=price_id
            ).first()
            if not plan:
                plan = SubscriptionPlan.objects.filter(
                    stripe_price_id_yearly=price_id
                ).first()
        
        # Update subscription type based on plan's tier_key
        if plan and plan.tier_key:
            profile.subscription_type = plan.tier_key
        elif plan:
            # Fallback: try to match plan name to tier
            plan_name_lower = plan.name.lower()
            if 'free' in plan_name_lower:
                profile.subscription_type = 'free'
            elif 'low' in plan_name_lower or 'basic' in plan_name_lower:
                profile.subscription_type = 'low'
            elif 'mid' in plan_name_lower or 'pro' in plan_name_lower:
                profile.subscription_type = 'mid'
            elif 'high' in plan_name_lower or 'enterprise' in plan_name_lower:
                profile.subscription_type = 'high'
        
        # Update AI tier from tier settings
        try:
            tier_settings = SubscriptionTierSettings.objects.get(tier=profile.subscription_type)
            profile.ai_tier = tier_settings.ai_tier
        except SubscriptionTierSettings.DoesNotExist:
            pass
        
        profile.subscription_start = timezone.now()
        profile.subscription_end = timezone.now() + timedelta(days=30)
        profile.save()
    except Exception as e:
        print(f"Error handling successful payment: {e}")

def handle_subscription_update(subscription):
    try:
        from engine.models import SubscriptionPlan, SubscriptionTierSettings
        
        profile = UserProfile.objects.get(stripe_subscription_id=subscription['id'])
        if subscription['status'] == 'active':
            profile.is_active = True
            # Try to update tier from plan if available
            if 'items' in subscription and subscription['items'].get('data'):
                price_id = subscription['items']['data'][0]['price']['id']
                plan = SubscriptionPlan.objects.filter(
                    stripe_price_id_monthly=price_id
                ).first()
                if not plan:
                    plan = SubscriptionPlan.objects.filter(
                        stripe_price_id_yearly=price_id
                    ).first()
                
                if plan and plan.tier_key:
                    profile.subscription_type = plan.tier_key
                    # Update AI tier
                    try:
                        tier_settings = SubscriptionTierSettings.objects.get(tier=plan.tier_key)
                        profile.ai_tier = tier_settings.ai_tier
                    except SubscriptionTierSettings.DoesNotExist:
                        pass
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


def verify_email_view(request, uidb64, token):
    """
    Verify user's email address using the token from the verification email.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your email has been verified! You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid or expired verification link. Please request a new one.')
        return redirect('login')


class UsernamePasswordResetForm(forms.Form):
    """Custom form that asks for username instead of email."""
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True,
        }),
        help_text='Enter your username to receive a password reset link and your username reminder.'
    )


def password_reset_request_view(request):
    """
    Handle password reset request form submission.
    Asks for username and sends both username reminder and password reset link.
    """
    if request.method == 'POST':
        form = UsernamePasswordResetForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username=username)
                send_password_reset_email(user, request)
                messages.success(request, 'If an account exists with that username, a password reset link and username reminder have been sent to your email address.')
                return redirect('login')
            except User.DoesNotExist:
                # Don't reveal if username exists or not (security best practice)
                messages.success(request, 'If an account exists with that username, a password reset link and username reminder have been sent.')
                return redirect('login')
    else:
        form = UsernamePasswordResetForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})


def password_reset_confirm_view(request, uidb64, token):
    """
    Handle password reset confirmation with new password.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
                return redirect('login')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'accounts/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'Invalid or expired password reset link. Please request a new one.')
        return redirect('password_reset_request')
