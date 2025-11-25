"""
Management command to create UserProfile for users who don't have one.

This is useful for fixing existing users (especially Google OAuth users)
who were created before the profile system was fully implemented.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from engine.models import UserProfile, SubscriptionPlan


class Command(BaseCommand):
    help = 'Create UserProfile for users who don\'t have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating profiles',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find all users without profiles
        users_without_profiles = []
        for user in User.objects.all():
            try:
                user.profile
            except UserProfile.DoesNotExist:
                users_without_profiles.append(user)
        
        if not users_without_profiles:
            self.stdout.write(self.style.SUCCESS('✓ All users have profiles'))
            return
        
        self.stdout.write(f'Found {len(users_without_profiles)} user(s) without profiles:')
        
        # Get or create free plan as default
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'description': 'Free tier with basic features',
                'price_monthly': 0,
                'price_yearly': 0,
                'max_datasets': 5,
                'max_sessions': 10,
                'max_file_size_mb': 10,
                'ai_tier': 'none',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created default Free plan'))
        
        created_count = 0
        for user in users_without_profiles:
            self.stdout.write(f'  - {user.username} ({user.email})')
            
            if not dry_run:
                try:
                    profile = UserProfile.objects.create(
                        user=user,
                        subscription_plan=free_plan
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Created profile for {user.username}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ✗ Failed to create profile for {user.username}: {e}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would create {len(users_without_profiles)} profile(s)'))
            self.stdout.write('Run without --dry-run to actually create profiles')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Created {created_count} profile(s)'))

