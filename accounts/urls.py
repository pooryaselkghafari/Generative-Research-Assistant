from django.urls import path
from . import views

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
]
