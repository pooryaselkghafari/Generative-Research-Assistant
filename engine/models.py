from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('low', 'Low Tier (AI Basic)'),
        ('mid', 'Mid Tier (AI RAG)'),
        ('high', 'High Tier (AI Fine-tuned)'),
    ]
    
    AI_TIER_CHOICES = [
        ('none', 'No AI Access'),
        ('general', 'General Fine-tuned Model'),
        ('rag', 'RAG (Retrieval-Augmented Generation)'),
        ('fine_tuned', 'User Fine-tuned Model'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='free')
    ai_tier = models.CharField(max_length=20, choices=AI_TIER_CHOICES, default='none')
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    max_datasets = models.IntegerField(null=True, blank=True)  # Null means use tier defaults
    max_sessions = models.IntegerField(null=True, blank=True)  # Null means use tier defaults
    max_file_size_mb = models.IntegerField(null=True, blank=True)  # Null means use tier defaults
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.subscription_type}"
    
    @property
    def is_subscription_active(self):
        if not self.subscription_end:
            return False
        return timezone.now() < self.subscription_end
    
    @property
    def days_remaining(self):
        if not self.subscription_end:
            return 0
        delta = self.subscription_end - timezone.now()
        return max(0, delta.days)
    
    def get_limits(self):
        """Get limits from tier settings or use defaults"""
        from .models import SubscriptionTierSettings
        try:
            tier_settings = SubscriptionTierSettings.objects.get(tier=self.subscription_type)
            return {
                'datasets': self.max_datasets if self.max_datasets is not None else tier_settings.max_datasets,
                'sessions': self.max_sessions if self.max_sessions is not None else tier_settings.max_sessions,
                'file_size': self.max_file_size_mb if self.max_file_size_mb is not None else tier_settings.max_file_size_mb,
            }
        except SubscriptionTierSettings.DoesNotExist:
            # Fallback to hardcoded defaults
            defaults = {
                'free': {'datasets': 5, 'sessions': 10, 'file_size': 10},
                'low': {'datasets': 25, 'sessions': 100, 'file_size': 50},
                'mid': {'datasets': 100, 'sessions': 500, 'file_size': 200},
                'high': {'datasets': -1, 'sessions': -1, 'file_size': 1000},  # -1 means unlimited
            }
            return defaults.get(self.subscription_type, defaults['free'])
    
    def get_ai_features(self):
        """Get AI features based on tier"""
        features = {
            'none': {
                'ai_enabled': False,
                'model_type': None,
                'rag_enabled': False,
                'fine_tuning_enabled': False,
            },
            'general': {
                'ai_enabled': True,
                'model_type': 'general_fine_tuned',
                'rag_enabled': False,
                'fine_tuning_enabled': False,
            },
            'rag': {
                'ai_enabled': True,
                'model_type': 'general_fine_tuned',
                'rag_enabled': True,
                'fine_tuning_enabled': False,
            },
            'fine_tuned': {
                'ai_enabled': True,
                'model_type': 'user_fine_tuned',
                'rag_enabled': True,
                'fine_tuning_enabled': True,
            },
        }
        return features.get(self.ai_tier, features['none'])

class Dataset(models.Model):
    name = models.CharField(max_length=200)
    file_path = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets', null=True, blank=True)
    file_size_mb = models.FloatField(default=0)
    
    class Meta:
        unique_together = ['name', 'user']  # Users can have datasets with same name
    
    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'No User'})"

class AnalysisSession(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=100, default='regression')
    formula = models.TextField()
    analysis_type = models.CharField(max_length=20, default='frequentist')
    options = models.JSONField(default=dict)
    # Foreign key with proper constraint: null/blank allowed but if set, must be valid
    dataset = models.ForeignKey(Dataset, null=True, blank=True, on_delete=models.SET_NULL, related_name='sessions', db_constraint=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    spotlight_rel = models.CharField(max_length=300, null=True, blank=True)
    fitted_model = models.BinaryField(null=True, blank=True)  # Store pickled fitted model
    ordinal_predictions = models.JSONField(null=True, blank=True)  # Store pre-generated ordinal predictions
    multinomial_predictions = models.JSONField(null=True, blank=True)  # Store pre-generated multinomial predictions

    def clean(self):
        """Validate foreign key constraint when dataset is explicitly set."""
        from django.core.exceptions import ValidationError
        if self.dataset_id is not None:
            # If dataset_id is set, verify it exists
            if not Dataset.objects.filter(pk=self.dataset_id).exists():
                raise ValidationError({'dataset': f"Dataset with id {self.dataset_id} does not exist."})
    
    def save(self, *args, **kwargs):
        """Override save to validate dataset foreign key constraint."""
        # Only validate the dataset foreign key, not all fields
        # This allows saving with partial data (e.g., during migrations or initial creation)
        if self.dataset_id is not None:
            self.clean()  # Only calls clean(), not full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'No User'})"

class SubscriptionTierSettings(models.Model):
    """Admin-configurable settings for each subscription tier"""
    TIER_CHOICES = [
        ('free', 'Free'),
        ('low', 'Low Tier (AI Basic)'),
        ('mid', 'Mid Tier (AI RAG)'),
        ('high', 'High Tier (AI Fine-tuned)'),
    ]
    
    AI_TIER_CHOICES = [
        ('none', 'No AI Access'),
        ('general', 'General Fine-tuned Model'),
        ('rag', 'RAG (Retrieval-Augmented Generation)'),
        ('fine_tuned', 'User Fine-tuned Model'),
    ]
    
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    max_datasets = models.IntegerField(default=5, help_text="Maximum number of datasets. Use -1 for unlimited.")
    max_sessions = models.IntegerField(default=10, help_text="Maximum number of analysis sessions. Use -1 for unlimited.")
    max_file_size_mb = models.IntegerField(default=10, help_text="Maximum file size in MB. Use -1 for unlimited.")
    ai_tier = models.CharField(max_length=20, choices=AI_TIER_CHOICES, default='none', help_text="AI access level for this tier")
    description = models.TextField(blank=True, help_text="Description of this tier")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Subscription Tier Settings"
        verbose_name_plural = "Subscription Tier Settings"
        ordering = ['tier']
    
    def __str__(self):
        return f"{self.get_tier_display()} Settings"

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    tier_key = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Must match tier in SubscriptionTierSettings (free, low, mid, high)")
    description = models.TextField()
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    features = models.JSONField(default=list, help_text="List of feature strings (e.g., ['AI Interpretation', 'RAG Support'])")
    ai_features = models.JSONField(default=list, help_text="AI-specific features for this plan")
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price_monthly']
    
    def __str__(self):
        return self.name
    
    def get_tier_settings(self):
        """Get associated tier settings"""
        if not self.tier_key:
            return None
        try:
            return SubscriptionTierSettings.objects.get(tier=self.tier_key)
        except SubscriptionTierSettings.DoesNotExist:
            return None

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    stripe_payment_intent_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"

class Page(models.Model):
    """Model for managing dynamic pages (like WordPress)"""
    PAGE_TYPE_CHOICES = [
        ('landing', 'Landing Page'),
        ('static', 'Static Page'),
        ('custom', 'Custom Page'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly version of the title (e.g., 'about-us')")
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, default='static')
    content = models.TextField(help_text="HTML content for the page. Use rich text editor.")
    
    # SEO Fields
    meta_description = models.CharField(max_length=300, blank=True, help_text="SEO meta description (recommended: 150-160 characters)")
    meta_keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords for SEO (e.g., 'research, analysis, statistics')")
    meta_title = models.CharField(max_length=200, blank=True, help_text="Custom meta title for search engines (defaults to page title if empty)")
    allow_indexing = models.BooleanField(default=True, help_text="Allow search engines to index this page")
    follow_links = models.BooleanField(default=True, help_text="Allow search engines to follow links on this page")
    canonical_url = models.URLField(blank=True, help_text="Canonical URL for SEO (prevents duplicate content issues)")
    
    # Open Graph / Social Media Tags
    og_title = models.CharField(max_length=200, blank=True, help_text="Title for social media sharing (defaults to page title)")
    og_description = models.TextField(blank=True, max_length=300, help_text="Description for social media sharing")
    og_image = models.URLField(blank=True, help_text="Image URL for social media sharing (recommended: 1200x630px)")
    og_type = models.CharField(max_length=50, default='website', help_text="Open Graph type (website, article, etc.)")
    
    # Publishing
    is_published = models.BooleanField(default=True, help_text="Unpublished pages won't be visible to public")
    is_default_landing = models.BooleanField(default=False, help_text="Set as default landing page (only one can be active)")
    template_name = models.CharField(max_length=100, blank=True, help_text="Optional custom template name")
    
    # Timestamps and ownership
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_pages')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_pages')
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Page"
        verbose_name_plural = "Pages"
    
    def __str__(self):
        status = "Published" if self.is_published else "Draft"
        return f"{self.title} ({status})"
    
    def save(self, *args, **kwargs):
        # If setting as default landing, unset others
        if self.is_default_landing and self.page_type == 'landing':
            Page.objects.filter(page_type='landing', is_default_landing=True).exclude(pk=self.pk).update(is_default_landing=False)
        super().save(*args, **kwargs)

class PrivacyPolicy(models.Model):
    """Model for managing privacy policy versions"""
    version = models.CharField(max_length=20, unique=True)
    content = models.TextField()
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"Privacy Policy v{self.version} ({self.effective_date})"

class TermsOfService(models.Model):
    """Model for managing terms of service versions"""
    version = models.CharField(max_length=20, unique=True)
    content = models.TextField()
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Terms of Service"
        verbose_name_plural = "Terms of Service"
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"Terms of Service v{self.version} ({self.effective_date})"

class TestResult(models.Model):
    """Store test execution results for tracking."""
    TEST_CATEGORIES = [
        ('security', 'Security Tests'),
        ('database', 'Database Tests'),
        ('performance', 'Performance Tests'),
        ('unit', 'Unit Tests'),
        ('integration', 'Integration Tests'),
        ('api', 'API Tests'),
        ('e2e', 'End-to-End Tests'),
        ('static_analysis', 'Static Analysis Tests'),
        ('dependency_scan', 'Dependency Vulnerability Scan'),
        ('coverage', 'Coverage Check'),
        ('backup', 'Backup/Restore Tests'),
        ('monitoring', 'Monitoring/Logging Tests'),
        ('cron', 'Cron/Scheduled Task Tests'),
        ('frontend', 'Frontend Tests'),
    ]
    
    category = models.CharField(max_length=20, choices=TEST_CATEGORIES)
    test_name = models.CharField(max_length=200)
    passed = models.BooleanField()
    score = models.FloatField(null=True, blank=True)  # 0-100
    total_tests = models.IntegerField()
    passed_tests = models.IntegerField()
    failed_tests = models.IntegerField()
    execution_time = models.FloatField()  # seconds
    details = models.JSONField(default=dict)  # Store detailed results
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['test_name', '-created_at']),
        ]
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{self.category}/{self.test_name} - {status} ({self.score}%)"
