# Generated migration to merge SubscriptionTierSettings into SubscriptionPlan

from django.db import migrations, models
import django.db.models.deletion


def migrate_tier_settings_to_plans(apps, schema_editor):
    """Migrate data from SubscriptionTierSettings to SubscriptionPlan"""
    SubscriptionTierSettings = apps.get_model('engine', 'SubscriptionTierSettings')
    SubscriptionPlan = apps.get_model('engine', 'SubscriptionPlan')
    
    # For each tier setting, update or create corresponding plan
    for tier_setting in SubscriptionTierSettings.objects.all():
        # Try to find existing plan by tier_key
        plan = SubscriptionPlan.objects.filter(tier_key=tier_setting.tier).first()
        
        if plan:
            # Update existing plan with tier settings data
            plan.max_datasets = tier_setting.max_datasets
            plan.max_sessions = tier_setting.max_sessions
            plan.max_file_size_mb = tier_setting.max_file_size_mb
            plan.ai_tier = tier_setting.ai_tier
            plan.workflow_template = tier_setting.workflow_template
            plan.save()
        else:
            # Create new plan from tier setting
            plan_name = tier_setting.get_tier_display()
            SubscriptionPlan.objects.create(
                name=plan_name,
                tier_key=tier_setting.tier,
                description=tier_setting.description or f"{plan_name} subscription plan",
                price_monthly=0,
                price_yearly=0,
                max_datasets=tier_setting.max_datasets,
                max_sessions=tier_setting.max_sessions,
                max_file_size_mb=tier_setting.max_file_size_mb,
                ai_tier=tier_setting.ai_tier,
                workflow_template=tier_setting.workflow_template,
                is_active=tier_setting.is_active,
            )


def migrate_user_profiles_to_plans(apps, schema_editor):
    """Migrate UserProfile.subscription_type to subscription_plan"""
    UserProfile = apps.get_model('engine', 'UserProfile')
    SubscriptionPlan = apps.get_model('engine', 'SubscriptionPlan')
    
    # Get or create free plan
    free_plan, _ = SubscriptionPlan.objects.get_or_create(
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
    
    # Migrate each user profile
    for profile in UserProfile.objects.all():
        if profile.subscription_type:
            # Try to find plan by tier_key matching subscription_type
            plan = SubscriptionPlan.objects.filter(tier_key=profile.subscription_type).first()
            if plan:
                profile.subscription_plan = plan
            else:
                # Fallback to free plan
                profile.subscription_plan = free_plan
        else:
            # No subscription type, assign free plan
            profile.subscription_plan = free_plan
        profile.save()


def reverse_migration(apps, schema_editor):
    """Reverse migration - not fully reversible, but prevents errors"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0027_alter_n8nworkflow_workflow_id'),
    ]

    operations = [
        # Step 1: Add new fields to SubscriptionPlan
        migrations.AddField(
            model_name='subscriptionplan',
            name='max_datasets',
            field=models.IntegerField(default=5, help_text='Maximum number of datasets. Use -1 for unlimited.'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='max_sessions',
            field=models.IntegerField(default=10, help_text='Maximum number of analysis sessions. Use -1 for unlimited.'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='max_file_size_mb',
            field=models.IntegerField(default=10, help_text='Maximum file size in MB. Use -1 for unlimited.'),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='ai_tier',
            field=models.CharField(
                choices=[('none', 'No AI Access'), ('general', 'General Fine-tuned Model'), ('rag', 'RAG (Retrieval-Augmented Generation)'), ('fine_tuned', 'User Fine-tuned Model')],
                default='none',
                help_text='AI access level for this plan',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='workflow_template',
            field=models.ForeignKey(
                blank=True,
                help_text="Agent Template (n8n workflow) used for chatbot access. Users without a workflow will see an upgrade message.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subscription_plans',
                to='engine.agenttemplate'
            ),
        ),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='name',
            field=models.CharField(help_text="Plan name (e.g., 'Free', 'Pro', 'Enterprise')", max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # Step 2: Add subscription_plan ForeignKey to UserProfile (nullable for now)
        migrations.AddField(
            model_name='userprofile',
            name='subscription_plan',
            field=models.ForeignKey(
                blank=True,
                help_text="User's current subscription plan",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='user_profiles',
                to='engine.subscriptionplan'
            ),
        ),
        
        # Step 3: Migrate data from SubscriptionTierSettings to SubscriptionPlan
        migrations.RunPython(migrate_tier_settings_to_plans, reverse_migration),
        
        # Step 4: Migrate UserProfile.subscription_type to subscription_plan
        migrations.RunPython(migrate_user_profiles_to_plans, reverse_migration),
        
        # Step 5: Remove old fields from UserProfile (after data migration)
        migrations.RemoveField(
            model_name='userprofile',
            name='subscription_type',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='ai_tier',
        ),
        
        # Step 6: Remove tier_key from SubscriptionPlan (no longer needed)
        migrations.RemoveField(
            model_name='subscriptionplan',
            name='tier_key',
        ),
        
        # Step 7: Drop SubscriptionTierSettings model
        migrations.DeleteModel(
            name='SubscriptionTierSettings',
        ),
    ]

