from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.utils.html import format_html
from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Dataset, AnalysisSession, UserProfile, SubscriptionPlan, Payment, Page,
    PrivacyPolicy, TermsOfService, SiteSettings,
    AgentTemplate, N8nWorkflow,
    AIFineTuningFile, AIFineTuningCommand, AIFineTuningTemplate, TestResult, Ticket,
    AIProvider
)
from . import admin_forms


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_subscription_plan')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__subscription_plan')
    
    def get_subscription_plan(self, obj):
        if hasattr(obj, 'profile') and obj.profile.subscription_plan:
            return obj.profile.subscription_plan.name
        return 'No Plan'
    get_subscription_plan.short_description = 'Subscription'

class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_user_display', 'file_size_mb', 'uploaded_at')
    list_filter = ('uploaded_at', 'user')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('uploaded_at',)
    raw_id_fields = ('user',)  # Better widget for selecting users
    
    def get_user_display(self, obj):
        """Display user with better formatting"""
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return format_html('<span style="color: #999;">No User</span>')
    get_user_display.short_description = 'User'
    get_user_display.admin_order_field = 'user__username'

class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_user_display', 'module', 'analysis_type', 'created_at')
    list_filter = ('module', 'analysis_type', 'created_at', 'user')
    search_fields = ('name', 'user__username', 'user__email', 'formula')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'dataset')  # Better widgets for selecting users/datasets
    
    def get_user_display(self, obj):
        """Display user with better formatting"""
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return format_html('<span style="color: #999;">No User</span>')
    get_user_display.short_description = 'User'
    get_user_display.admin_order_field = 'user__username'

class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Unified admin interface for subscription plans with all settings in one place."""
    list_display = ('name', 'price_monthly', 'price_yearly', 'max_datasets', 'max_sessions', 'ai_tier', 'workflow_template', 'is_active', 'updated_at')
    list_filter = ('is_active', 'ai_tier', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'description', 'is_active'),
            'description': 'Basic information about this subscription plan.'
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_yearly', 'stripe_price_id_monthly', 'stripe_price_id_yearly'),
            'description': 'Pricing information for monthly and yearly subscriptions. Connect to Stripe using the Price IDs.'
        }),
        ('Features', {
            'fields': ('features', 'ai_features'),
            'description': 'List of features and AI-specific features for this plan. These are displayed to users on the subscription page.'
        }),
        ('Resource Limits', {
            'fields': ('max_datasets', 'max_sessions', 'max_file_size_mb'),
            'description': 'Resource limits for this plan. Use -1 for unlimited. Users can override these in their profile if needed.'
        }),
        ('AI & Workflow Configuration', {
            'fields': ('ai_tier', 'workflow_template'),
            'description': 'AI access level and the agent template (n8n workflow) used for chatbot access. Users without a workflow will see an upgrade message.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_plan', 'get_ai_tier', 'get_datasets_count', 'get_sessions_count', 'is_active', 'subscription_status')
    list_filter = ('subscription_plan', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'subscription_plan__name')
    readonly_fields = ('created_at', 'updated_at', 'subscription_status', 'usage_stats', 'get_ai_tier')
    raw_id_fields = ('subscription_plan',)
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_active')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'get_ai_tier', 'subscription_start', 'subscription_end', 'subscription_status'),
            'description': 'User\'s subscription plan. AI tier is determined by the plan.'
        }),
        ('Stripe Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Custom Limits (Optional)', {
            'fields': ('max_datasets', 'max_sessions', 'max_file_size_mb'),
            'description': 'Override plan defaults. Leave blank to use plan defaults. Use -1 for unlimited.'
        }),
        ('Usage Statistics', {
            'fields': ('usage_stats',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_ai_tier(self, obj):
        """Display AI tier from subscription plan"""
        if obj.subscription_plan:
            return obj.subscription_plan.get_ai_tier_display()
        return 'No AI Access'
    get_ai_tier.short_description = 'AI Tier'
    
    def subscription_status(self, obj):
        """Display subscription status"""
        if obj.is_subscription_active:
            days = obj.days_remaining
            if days > 30:
                color = 'green'
            elif days > 7:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">Active ({} days remaining)</span>',
                color, days
            )
        return format_html('<span style="color: red;">Inactive</span>')
    subscription_status.short_description = 'Status'
    
    def get_datasets_count(self, obj):
        """Show current datasets vs limit"""
        count = obj.user.datasets.count()
        limits = obj.get_limits()
        max_ds = limits['datasets']
        if max_ds == -1:
            return f"{count} / ∞"
        return f"{count} / {max_ds}"
    get_datasets_count.short_description = 'Datasets'
    
    def get_sessions_count(self, obj):
        """Show current sessions vs limit"""
        count = obj.user.sessions.count()
        limits = obj.get_limits()
        max_sess = limits['sessions']
        if max_sess == -1:
            return f"{count} / ∞"
        return f"{count} / {max_sess}"
    get_sessions_count.short_description = 'Sessions'
    
    def usage_stats(self, obj):
        """Display usage statistics"""
        limits = obj.get_limits()
        datasets_count = obj.user.datasets.count()
        sessions_count = obj.user.sessions.count()
        
        datasets_pct = (datasets_count / limits['datasets'] * 100) if limits['datasets'] != -1 else 0
        sessions_pct = (sessions_count / limits['sessions'] * 100) if limits['sessions'] != -1 else 0
        
        html = f"""
        <table style="width: 100%;">
            <tr>
                <th style="text-align: left;">Resource</th>
                <th style="text-align: left;">Used</th>
                <th style="text-align: left;">Limit</th>
                <th style="text-align: left;">Usage</th>
            </tr>
            <tr>
                <td>Datasets</td>
                <td>{datasets_count}</td>
                <td>{'∞' if limits['datasets'] == -1 else limits['datasets']}</td>
                <td>{'100%' if limits['datasets'] == -1 else f'{datasets_pct:.1f}%'}</td>
            </tr>
            <tr>
                <td>Sessions</td>
                <td>{sessions_count}</td>
                <td>{'∞' if limits['sessions'] == -1 else limits['sessions']}</td>
                <td>{'100%' if limits['sessions'] == -1 else f'{sessions_pct:.1f}%'}</td>
            </tr>
            <tr>
                <td>Max File Size</td>
                <td>-</td>
                <td>{'∞' if limits['file_size'] == -1 else f"{limits['file_size']} MB"}</td>
                <td>-</td>
            </tr>
        </table>
        """
        return mark_safe(html)
    usage_stats.short_description = 'Usage Statistics'

class PrivacyPolicyAdminForm(forms.ModelForm):
    """Custom form for Privacy Policy with CKEditor rich text editor."""
    class Meta:
        model = PrivacyPolicy
        fields = '__all__'
        widgets = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check for CKEditor dynamically
        try:
            from ckeditor.widgets import CKEditorWidget
            # Use CKEditor widget for content field
            widget = CKEditorWidget(config_name='default')
            self.fields['content'].widget = widget
        except ImportError:
            # Fallback to textarea if CKEditor not available
            self.fields['content'].widget = forms.Textarea(attrs={
                'rows': 30, 
                'cols': 80, 
                'style': 'width: 100%; font-family: monospace;'
            })

class PrivacyPolicyAdmin(admin.ModelAdmin):
    form = PrivacyPolicyAdminForm
    list_display = ('version', 'effective_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'effective_date')
    search_fields = ('version', 'content')
    fieldsets = (
        ('Version Information', {
            'fields': ('version', 'effective_date', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'Use the rich text editor below to format your privacy policy with HTML, headings, lists, and more.'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

class TermsOfServiceAdminForm(forms.ModelForm):
    """Custom form for Terms of Service with CKEditor rich text editor."""
    class Meta:
        model = TermsOfService
        fields = '__all__'
        widgets = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check for CKEditor dynamically
        try:
            from ckeditor.widgets import CKEditorWidget
            # Use CKEditor widget for content field
            widget = CKEditorWidget(config_name='default')
            self.fields['content'].widget = widget
        except ImportError:
            # Fallback to textarea if CKEditor not available
            self.fields['content'].widget = forms.Textarea(attrs={
                'rows': 30, 
                'cols': 80, 
                'style': 'width: 100%; font-family: monospace;'
            })

class TermsOfServiceAdmin(admin.ModelAdmin):
    form = TermsOfServiceAdminForm
    list_display = ('version', 'effective_date', 'is_active', 'created_at')
    list_filter = ('is_active', 'effective_date')
    search_fields = ('version', 'content')
    fieldsets = (
        ('Version Information', {
            'fields': ('version', 'effective_date', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'Use the rich text editor below to format your terms of service with HTML, headings, lists, and more.'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__username', 'stripe_payment_intent_id')
    readonly_fields = ('created_at',)

class PageAdminForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = '__all__'
        widgets = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check for CKEditor dynamically
        try:
            from ckeditor.widgets import CKEditorWidget
            # Create custom config that includes subscription_plans plugin
            from ckeditor.configs import DEFAULT_CONFIG
            custom_config = DEFAULT_CONFIG.copy()
            custom_config['extraPlugins'] = ','.join([
                custom_config.get('extraPlugins', ''),
                'subscription_plans'
            ]).strip(',').replace(',,', ',')
            # Use settings config and just ensure subscription_plans plugin is included
            widget = CKEditorWidget(config_name='default')
            # The config from settings.py will be used, which already has maximize
            self.fields['content'].widget = widget
        except ImportError:
            # Fallback to textarea if CKEditor not available
            self.fields['content'].widget = forms.Textarea(attrs={
                'rows': 20, 
                'cols': 80, 
                'style': 'width: 100%; font-family: monospace;'
            })

class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    list_display = ('title', 'slug', 'page_type', 'is_published', 'is_default_landing', 'seo_status', 'preview_link', 'created_at', 'updated_at')
    list_filter = ('page_type', 'is_published', 'is_default_landing', 'allow_indexing', 'created_at')
    search_fields = ('title', 'slug', 'content', 'meta_description', 'meta_keywords')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'preview_link', 'seo_status')
    
    def seo_status(self, obj):
        """Display SEO completeness status"""
        missing = []
        if not obj.meta_description:
            missing.append('description')
        if not obj.meta_keywords:
            missing.append('keywords')
        if not obj.meta_title and not obj.title:
            missing.append('title')
        
        if not missing:
            return format_html('<span style="color: green;">✓ Complete</span>')
        else:
            return format_html('<span style="color: orange;" title="Missing: {}">⚠ {}</span>', ', '.join(missing), len(missing))
    seo_status.short_description = 'SEO Status'
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'page_type', 'template_name')
        }),
        ('Page Content', {
            'fields': ('content',),
            'description': 'Use the rich text editor below to format your content with colors, headings, lists, and more.'
        }),
        ('SEO - Search Engine Optimization', {
            'fields': (
                'meta_title',
                'meta_description',
                'meta_keywords',
                'canonical_url',
                ('allow_indexing', 'follow_links'),
            ),
            'description': 'Optimize your page for search engines. Leave meta_title empty to use the page title.'
        }),
        ('Social Media (Open Graph)', {
            'fields': (
                'og_title',
                'og_description',
                'og_image',
                'og_type',
            ),
            'description': 'Customize how your page appears when shared on social media platforms.',
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_default_landing')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by', 'preview_link'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def preview_link(self, obj):
        if obj.slug:
            if obj.page_type == 'landing':
                url = '/'
            else:
                url = f'/page/{obj.slug}/'
            return format_html('<a href="{}" target="_blank">View Page</a>', url)
        return '-'
    preview_link.short_description = 'Preview'

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Dataset, DatasetAdmin)
admin.site.register(AnalysisSession, AnalysisSessionAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(PrivacyPolicy, PrivacyPolicyAdmin)
admin.site.register(TermsOfService, TermsOfServiceAdmin)


class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin interface for Site Settings (Google Analytics, etc.)"""
    fieldsets = (
        ('Google Analytics', {
            'fields': ('is_active', 'google_analytics_id', 'google_analytics_code'),
            'description': 'Enter either a Google Analytics ID (e.g., G-8FHJC3M9SD) or paste the full Google Analytics code. If both are provided, the custom code will be used.'
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion (we need at least one instance)
        return False

admin.site.register(SiteSettings, SiteSettingsAdmin)


class AgentTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Agent Templates."""
    list_display = ('name', 'status', 'visibility', 'mode_key', 'workflow', 'created_at', 'updated_at')
    list_filter = ('status', 'visibility', 'created_at')
    search_fields = ('name', 'description', 'mode_key', 'n8n_webhook_url')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status', 'visibility', 'workflow')
        }),
        ('n8n Configuration', {
            'fields': ('n8n_webhook_url', 'mode_key', 'default_parameters'),
            'description': 'Configure the n8n webhook URL and optional mode key for chatbot routing.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('created_by')

admin.site.register(AgentTemplate, AgentTemplateAdmin)


class N8nWorkflowAdmin(admin.ModelAdmin):
    """Read-only admin for n8n workflows with sync action."""
    list_display = ('name', 'workflow_id', 'active', 'updated_at', 'linked_templates')
    search_fields = ('name', 'workflow_id', 'description')
    list_filter = ('active',)
    readonly_fields = ('workflow_id', 'name', 'active', 'version_id', 'webhook_id', 'test_url', 'production_url',
                       'tags', 'description', 'data', 'n8n_created_at', 'n8n_updated_at', 'created_at', 'updated_at')
    actions = ['sync_from_n8n']

    def linked_templates(self, obj):
        count = obj.agent_templates.count()
        if count == 0:
            return 'None'
        url = reverse('admin:engine_agenttemplate_changelist') + f'?workflow__id__exact={obj.id}'
        return format_html('<a href="{}">{} template(s)</a>', url, count)
    linked_templates.short_description = 'Agent Templates'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.method == 'POST':
            return False
        return super().has_change_permission(request, obj)

    def sync_from_n8n(self, request, queryset):
        from django.utils.dateparse import parse_datetime
        from engine.services.n8n_api_client import N8nAPIClient

        client = N8nAPIClient()
        try:
            workflows = client.list_workflows()
        except Exception as exc:
            self.message_user(request, f"Failed to fetch workflows from n8n: {exc}", level='error')
            return

        created = 0
        updated = 0

        for wf in workflows:
            defaults = {
                'name': wf.get('name') or f"Workflow {wf.get('id')}",
                'active': wf.get('active', False),
                'tags': wf.get('tags') or [],
                'version_id': str(wf.get('versionId') or ''),
                'webhook_id': str(wf.get('webhookId') or ''),
                'test_url': wf.get('testUrl', '') or '',
                'production_url': wf.get('productionUrl', '') or '',
                'description': (wf.get('settings') or {}).get('notes', ''),
                'data': wf,
                'n8n_created_at': parse_datetime(wf.get('createdAt')) if wf.get('createdAt') else None,
                'n8n_updated_at': parse_datetime(wf.get('updatedAt')) if wf.get('updatedAt') else None,
            }
            _, is_created = N8nWorkflow.objects.update_or_create(
                workflow_id=wf.get('id'),
                defaults=defaults
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.message_user(request, f"Synced {len(workflows)} workflows (created {created}, updated {updated}).")

    sync_from_n8n.short_description = "Sync workflows from n8n"


admin.site.register(N8nWorkflow, N8nWorkflowAdmin)


class AIFineTuningFileAdmin(admin.ModelAdmin):
    """Admin interface for AI fine-tuning files."""
    list_display = ('name', 'file_type', 'is_active', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type', 'is_active', 'uploaded_at')
    search_fields = ('name', 'description')
    readonly_fields = ('uploaded_at', 'updated_at')
    list_editable = ('is_active',)


class AIFineTuningCommandAdmin(admin.ModelAdmin):
    """
    Admin interface for AI fine-tuning commands with template support.
    
    Provides template selection and JSON editing capabilities for
    fine-tuning command configuration.
    """
    list_display = ('command_type', 'status', 'provider', 'created_by', 'created_at', 'get_files_count')
    list_filter = ('command_type', 'status', 'provider', 'created_at')
    search_fields = ('description', 'result')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'status')
    filter_horizontal = ('files',)
    raw_id_fields = ('provider',)
    
    fieldsets = (
        ('Command Information', {
            'fields': ('command_type', 'description', 'provider')
        }),
        ('Command Data', {
            'fields': ('template_select', 'command_data'),
            'classes': ('wide',)
        }),
        ('Files', {
            'fields': ('files',),
            'classes': ('collapse',)
        }),
        ('Status & Metadata', {
            'fields': ('status', 'created_by', 'created_at', 'updated_at', 'completed_at', 'result'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        """Media files for admin interface."""
        js = ('admin/js/ai_finetuning_command_admin.js',)
        css = {
            'all': ('admin/css/ai_finetuning_command_admin.css',)
        }
    
    def get_files_count(self, obj):
        """
        Return count of associated files.
        
        Args:
            obj: AIFineTuningCommand instance
            
        Returns:
            int: Number of associated files
        """
        return obj.files.count()
    get_files_count.short_description = 'Files'
    
    def save_model(self, request, obj, form, change):
        """
        Save model and set created_by if new.
        
        Args:
            request: Django request object
            obj: AIFineTuningCommand instance
            form: Form instance
            change: Boolean indicating if this is an update
        """
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(AIFineTuningFile, AIFineTuningFileAdmin)
admin.site.register(AIFineTuningCommand, AIFineTuningCommandAdmin)


class TestResultAdmin(admin.ModelAdmin):
    """Admin interface for test results."""
    list_display = ('category', 'test_name', 'score', 'passed', 'passed_tests', 'total_tests', 'execution_time', 'created_at')
    list_filter = ('category', 'passed', 'created_at')
    search_fields = ('test_name', 'category')
    readonly_fields = ('created_at', 'execution_time', 'score', 'passed', 'passed_tests', 'failed_tests', 'total_tests')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Test Information', {
            'fields': ('category', 'test_name', 'passed', 'score')
        }),
        ('Test Results', {
            'fields': ('total_tests', 'passed_tests', 'failed_tests', 'execution_time')
        }),
        ('Details', {
            'fields': ('details', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """Test results are created automatically by test suites."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Test results should not be manually edited."""
        return False


admin.site.register(TestResult, TestResultAdmin)


class LogEntryAdmin(admin.ModelAdmin):
    """Admin interface for Django admin activity logs."""
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'get_change_message')
    list_filter = ('action_time', 'action_flag', 'content_type')
    search_fields = ('user__username', 'object_repr', 'change_message')
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    ordering = ('-action_time',)
    date_hierarchy = 'action_time'
    
    fieldsets = (
        ('Action Information', {
            'fields': ('action_time', 'user', 'action_flag')
        }),
        ('Object Information', {
            'fields': ('content_type', 'object_id', 'object_repr')
        }),
        ('Change Details', {
            'fields': ('change_message',),
            'classes': ('collapse',)
        }),
    )
    
    def get_change_message(self, obj):
        """Display change message with better formatting."""
        if obj.change_message:
            # Truncate long messages
            msg = obj.change_message
            if len(msg) > 100:
                msg = msg[:100] + '...'
            return format_html('<span style="font-size: 0.9em;">{}</span>', msg)
        return '-'
    get_change_message.short_description = 'Change Message'
    
    def has_add_permission(self, request):
        """Log entries are created automatically by Django."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Log entries should not be manually edited."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup (with proper permissions)."""
        return request.user.is_superuser


admin.site.register(LogEntry, LogEntryAdmin)


class TicketAdmin(admin.ModelAdmin):
    """
    Admin interface for managing tickets.
    """
    list_display = ('id', 'title', 'user', 'status', 'priority', 'assigned_to', 'created_at', 'resolved_at')
    list_filter = ('status', 'priority', 'created_at', 'assigned_to')
    search_fields = ('title', 'description', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    raw_id_fields = ('user', 'assigned_to')
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('user', 'title', 'description', 'status', 'priority')
        }),
        ('Assignment', {
            'fields': ('assigned_to',)
        }),
        ('Admin Response', {
            'fields': ('admin_notes', 'admin_response'),
            'description': 'admin_notes is internal only, admin_response is visible to user'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'assigned_to')
    
    def get_readonly_fields(self, request, obj=None):
        """Make resolved_at readonly"""
        readonly = list(self.readonly_fields)
        if obj and obj.resolved_at:
            readonly.append('resolved_at')
        return readonly

admin.site.register(Ticket, TicketAdmin)


class AIProviderAdmin(admin.ModelAdmin):
    """
    Admin interface for AI Provider configuration.
    
    Provides a user-friendly form for configuring AI provider settings,
    API keys, and testing connections.
    """
    list_display = ('name', 'provider_type', 'is_active', 'is_default', 'test_status', 'last_tested_at', 'created_by')
    list_filter = ('provider_type', 'is_active', 'is_default', 'test_status', 'created_at')
    search_fields = ('name', 'base_model', 'fine_tuned_model_id')
    readonly_fields = ('created_at', 'updated_at', 'last_tested_at', 'test_status', 'test_message', 'created_by')
    raw_id_fields = ('created_by',)
    
    fieldsets = (
        ('Provider Information', {
            'fields': ('name', 'provider_type', 'is_active', 'is_default'),
            'description': 'Configure the AI provider settings. Only one provider can be set as default.'
        }),
        ('API Configuration', {
            'fields': ('api_key', 'api_base_url', 'organization_id'),
            'description': '⚠️ API keys are encrypted for security. Enter your API key from your AI provider dashboard.'
        }),
        ('Model Configuration', {
            'fields': ('base_model', 'fine_tuned_model_id'),
            'description': 'Base model identifier and fine-tuned model ID (if available).'
        }),
        ('Connection Test', {
            'fields': ('test_status', 'test_message', 'last_tested_at'),
            'description': 'Test the connection to verify API credentials are correct. Use the "Test Connection" action below.',
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['test_connection', 'set_as_default', 'activate_providers', 'deactivate_providers']
    
    def save_model(self, request, obj, form, change):
        """Set created_by if new."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def test_connection(self, request, queryset):
        """
        Test connection to selected AI providers.
        
        Args:
            request: Django request object
            queryset: Selected AIProvider objects
        """
        from engine.integrations.ai_provider import AIService
        
        tested = 0
        successful = 0
        failed = 0
        
        for provider in queryset:
            tested += 1
            try:
                # Temporarily set as active for testing
                original_active = provider.is_active
                provider.is_active = True
                provider.save()
                
                # Test connection - pass provider_id to use this specific provider
                result = AIService.test_model("Test connection", provider_id=provider.id)
                
                if result.get('success'):
                    successful += 1
                    self.message_user(
                        request,
                        f'✓ {provider.name}: Connection test successful',
                        level='SUCCESS'
                    )
                else:
                    failed += 1
                    self.message_user(
                        request,
                        f'✗ {provider.name}: {result.get("message", "Connection test failed")}',
                        level='ERROR'
                    )
                
                # Restore original active status
                provider.is_active = original_active
                provider.save()
                
            except Exception as e:
                failed += 1
                self.message_user(
                    request,
                    f'✗ {provider.name}: Error - {str(e)}',
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f'Tested {tested} provider(s): {successful} successful, {failed} failed',
            level='INFO' if failed == 0 else 'WARNING'
        )
    test_connection.short_description = "Test connection to selected providers"
    
    def set_as_default(self, request, queryset):
        """Set selected provider as default."""
        if queryset.count() != 1:
            self.message_user(
                request,
                'Please select exactly one provider to set as default',
                level='ERROR'
            )
            return
        
        provider = queryset.first()
        provider.is_default = True
        provider.is_active = True
        provider.save()
        
        self.message_user(
            request,
            f'✓ {provider.name} set as default provider',
            level='SUCCESS'
        )
    set_as_default.short_description = "Set as default provider"
    
    def activate_providers(self, request, queryset):
        """Activate selected providers."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'✓ Activated {count} provider(s)',
            level='SUCCESS'
        )
    activate_providers.short_description = "Activate selected providers"
    
    def deactivate_providers(self, request, queryset):
        """Deactivate selected providers."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'✓ Deactivated {count} provider(s)',
            level='SUCCESS'
        )
    deactivate_providers.short_description = "Deactivate selected providers"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            qs = super().get_queryset(request)
            return qs.select_related('created_by')
        except Exception as e:
            # Fallback if select_related fails (e.g., table doesn't exist, missing field)
            logger.error(f"Error in AIProviderAdmin.get_queryset: {e}", exc_info=True)
            try:
                # Try without select_related
                return super().get_queryset(request)
            except Exception as e2:
                # Last resort: return empty queryset to prevent 500 error
                logger.error(f"Critical error in AIProviderAdmin.get_queryset: {e2}", exc_info=True)
                return AIProvider.objects.none()
    
    def get_list_display(self, request):
        """Safely get list_display with error handling."""
        try:
            return self.list_display
        except Exception:
            # Fallback to basic fields if there's an error
            return ('name', 'provider_type', 'is_active')

# Register AIProvider with error handling
try:
    admin.site.register(AIProvider, AIProviderAdmin)
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error registering AIProvider in admin: {e}", exc_info=True)
    # Try to register with minimal config as fallback
    try:
        class MinimalAIProviderAdmin(admin.ModelAdmin):
            list_display = ('name', 'provider_type', 'is_active')
        admin.site.register(AIProvider, MinimalAIProviderAdmin)
        logger.warning("Registered AIProvider with minimal admin configuration")
    except Exception as e2:
        logger.error(f"Failed to register AIProvider even with minimal config: {e2}")


# AIFineTuningTemplate model exists but is not exposed in admin
# Templates are managed through the command data field

# Setup custom form for AIFineTuningCommandAdmin
try:
    from engine.admin_forms import AIFineTuningCommandAdminForm
    AIFineTuningCommandAdmin.form = AIFineTuningCommandAdminForm
except ImportError:
    pass

# Customize admin site
admin.site.site_header = "Generative Research Assistant Administration"
admin.site.site_title = "Generative Research Assistant Admin"
admin.site.index_title = "Welcome to Generative Research Assistant Administration"
