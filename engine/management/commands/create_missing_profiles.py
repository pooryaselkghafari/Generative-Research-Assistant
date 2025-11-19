"""
Management command to create UserProfile for users who don't have one.

This is useful for fixing existing users (especially Google OAuth users)
who were created before the profile system was fully implemented.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from engine.models import UserProfile, SubscriptionTierSettings


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
        
        # Try to get free tier settings
        try:
            tier_settings = SubscriptionTierSettings.objects.get(tier='free')
            default_ai_tier = tier_settings.ai_tier
        except SubscriptionTierSettings.DoesNotExist:
            default_ai_tier = 'none'
            self.stdout.write(self.style.WARNING('⚠ SubscriptionTierSettings not found, using default ai_tier="none"'))
        
        created_count = 0
        for user in users_without_profiles:
            self.stdout.write(f'  - {user.username} ({user.email})')
            
            if not dry_run:
                try:
                    profile = UserProfile.objects.create(
                        user=user,
                        subscription_type='free',
                        ai_tier=default_ai_tier
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

