"""
Custom template tags for subscription plans
"""
from django import template
from engine.models import SubscriptionPlan

register = template.Library()

@register.inclusion_tag('engine/subscription_plans_widget.html', takes_context=True)
def subscription_plans(context, featured_plan_index=2):
    """
    Render subscription plans dynamically.
    
    Usage in CKEditor:
    {% load subscription_tags %}
    {% subscription_plans %}
    
    Or with custom featured plan:
    {% subscription_plans featured_plan_index=3 %}
    """
    plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly'))
    plans_count = len(plans)
    
    return {
        'plans': plans,
        'plans_count': plans_count,
        'featured_plan_index': featured_plan_index,
        'request': context.get('request'),
    }

@register.simple_tag
def subscription_plans_count():
    """Return the count of active subscription plans"""
    return SubscriptionPlan.objects.filter(is_active=True).count()

