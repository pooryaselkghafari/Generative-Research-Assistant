from django.urls import path
from . import views
from . import ticket_views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('subscription/checkout/<int:plan_id>/', views.create_checkout_session, name='checkout'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    # Email verification and password reset
    path('verify-email/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    # Ticket system
    path('tickets/', ticket_views.ticket_list, name='ticket_list'),
    path('tickets/create/', ticket_views.ticket_create, name='ticket_create'),
    path('tickets/<int:ticket_id>/', ticket_views.ticket_detail, name='ticket_detail'),
]
