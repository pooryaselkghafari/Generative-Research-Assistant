"""
Management command to check chatbot access for a specific user.
Helps diagnose why users see upgrade popup even with connected workflows.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from engine.models import UserProfile, SubscriptionPlan, AgentTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Check chatbot access for a user and diagnose issues'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username to check access for'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{username}' not found"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"\nChecking chatbot access for: {user.username} (ID: {user.id})"))
        self.stdout.write("=" * 60)
        
        # Check user profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR("✗ UserProfile does not exist"))
            self.stdout.write("  → Run: python manage.py create_missing_profiles")
            return
        
        self.stdout.write(self.style.SUCCESS("✓ UserProfile exists"))
        
        # Check subscription plan
        if not profile.subscription_plan:
            self.stdout.write(self.style.ERROR("✗ No subscription plan assigned"))
            self.stdout.write("  → Assign a subscription plan in the admin")
            return
        
        plan = profile.subscription_plan
        self.stdout.write(self.style.SUCCESS(f"✓ Subscription plan: '{plan.name}'"))
        self.stdout.write(f"  - Plan is_active: {plan.is_active}")
        self.stdout.write(f"  - Max datasets: {plan.max_datasets}")
        self.stdout.write(f"  - Max sessions: {plan.max_sessions}")
        
        # Check workflow template
        if not plan.workflow_template:
            self.stdout.write(self.style.ERROR("✗ No workflow_template connected to subscription plan"))
            self.stdout.write("  → In admin, edit the subscription plan and select a workflow_template")
            return
        
        template = plan.workflow_template
        self.stdout.write(self.style.SUCCESS(f"✓ Workflow template: '{template.name}' (ID: {template.id})"))
        self.stdout.write(f"  - Status: {template.status}")
        self.stdout.write(f"  - Visibility: {template.visibility}")
        self.stdout.write(f"  - Webhook URL: {template.n8n_webhook_url}")
        self.stdout.write(f"  - Mode key: {template.mode_key or '(none)'}")
        
        # Check if template is usable
        if not template.is_usable():
            self.stdout.write(self.style.ERROR(f"✗ Template is NOT usable (status: '{template.status}')"))
            self.stdout.write("  → Template status must be 'active' to be usable")
            self.stdout.write("  → In admin, edit the AgentTemplate and set status to 'active'")
            return
        
        self.stdout.write(self.style.SUCCESS("✓ Template is usable"))
        
        # Check visibility
        if template.visibility == 'internal' and not user.is_staff:
            self.stdout.write(self.style.ERROR("✗ Template is 'internal' but user is not staff"))
            self.stdout.write("  → Either make user staff or change template visibility to 'customer_facing'")
            return
        
        self.stdout.write(self.style.SUCCESS("✓ User has permission to use template"))
        
        # Final check
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✓ User SHOULD have chatbot access!"))
        self.stdout.write(f"  Template: {template.name}")
        self.stdout.write(f"  Webhook: {template.n8n_webhook_url}")
        self.stdout.write("\nIf user still sees upgrade popup, check:")
        self.stdout.write("  1. Browser cache (hard refresh: Ctrl+Shift+R)")
        self.stdout.write("  2. Server logs for errors")
        self.stdout.write("  3. Network tab in browser dev tools for API response")

