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
    SubscriptionTierSettings, PrivacyPolicy, TermsOfService,
    AIFineTuningFile, AIFineTuningCommand, AIFineTuningTemplate, TestResult
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_subscription_type')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__subscription_type')
    
    def get_subscription_type(self, obj):
        return obj.profile.subscription_type
    get_subscription_type.short_description = 'Subscription'

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

class SubscriptionTierSettingsAdmin(admin.ModelAdmin):
    list_display = ('tier', 'max_datasets', 'max_sessions', 'max_file_size_mb', 'ai_tier', 'is_active', 'updated_at')
    list_filter = ('is_active', 'ai_tier', 'tier')
    fieldsets = (
        ('Tier Information', {
            'fields': ('tier', 'description', 'is_active')
        }),
        ('Resource Limits', {
            'fields': ('max_datasets', 'max_sessions', 'max_file_size_mb'),
            'description': 'Use -1 for unlimited. These limits apply to all users on this tier unless overridden in their profile.'
        }),
        ('AI Features', {
            'fields': ('ai_tier',),
            'description': 'AI access level for this tier. Users on this tier will have access to the selected AI features.'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier_key', 'price_monthly', 'price_yearly', 'is_active', 'tier_settings_link')
    list_filter = ('is_active', 'tier_key')
    search_fields = ('name', 'description', 'tier_key')
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'tier_key', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_yearly', 'stripe_price_id_monthly', 'stripe_price_id_yearly')
        }),
        ('Features', {
            'fields': ('features', 'ai_features'),
            'description': 'List of features and AI-specific features for this plan. These are displayed to users.'
        }),
    )
    
    def tier_settings_link(self, obj):
        """Link to tier settings"""
        if obj.tier_key:
            url = reverse('admin:engine_subscriptiontiersettings_change', args=[obj.get_tier_settings().id]) if obj.get_tier_settings() else '#'
            if url != '#':
                return format_html('<a href="{}">View Tier Settings</a>', url)
        return '-'
    tier_settings_link.short_description = 'Tier Settings'

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_type', 'ai_tier', 'get_datasets_count', 'get_sessions_count', 'is_active', 'subscription_status')
    list_filter = ('subscription_type', 'ai_tier', 'is_active')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'subscription_status', 'usage_stats')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_active')
        }),
        ('Subscription', {
            'fields': ('subscription_type', 'ai_tier', 'subscription_start', 'subscription_end', 'subscription_status')
        }),
        ('Stripe Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Custom Limits (Optional)', {
            'fields': ('max_datasets', 'max_sessions', 'max_file_size_mb'),
            'description': 'Override tier defaults. Leave blank to use tier defaults. Use -1 for unlimited.'
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
admin.site.register(SubscriptionTierSettings, SubscriptionTierSettingsAdmin)
admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(PrivacyPolicy, PrivacyPolicyAdmin)
admin.site.register(TermsOfService, TermsOfServiceAdmin)


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
    list_display = ('command_type', 'status', 'created_by', 'created_at', 'get_files_count')
    list_filter = ('command_type', 'status', 'created_at')
    search_fields = ('description', 'result')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'status')
    filter_horizontal = ('files',)
    
    fieldsets = (
        ('Command Information', {
            'fields': ('command_type', 'description')
        }),
        ('Command Data', {
            'fields': ('template_select', 'command_data'),
            'description': (
                '📋 Select a template to automatically pre-fill the command data with sensible defaults, '
                'or edit the JSON directly. Templates are automatically generated based on your selected command type.'
            ),
            'classes': ('wide',)
        }),
        ('Files', {
            'fields': ('files',),
            'classes': ('collapse',)
        }),
        ('Status & Metadata', {
            'fields': ('status', 'created_by', 'created_at', 'updated_at', 'completed_at', 'result'),
            'description': 'Status is automatically managed by the system during command processing.',
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
