from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django import forms
from .models import Dataset, AnalysisSession, UserProfile, SubscriptionPlan, Payment, Page

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

class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'price_yearly', 'max_datasets', 'max_sessions', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

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
            self.fields['content'].widget = CKEditorWidget(config_name='default')
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
admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Page, PageAdmin)

# Customize admin site
admin.site.site_header = "Generative Research Assistant Administration"
admin.site.site_title = "Generative Research Assistant Admin"
admin.site.index_title = "Welcome to Generative Research Assistant Administration"
