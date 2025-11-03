from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='free')
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    max_datasets = models.IntegerField(default=5)  # Free tier limit
    max_sessions = models.IntegerField(default=10)  # Free tier limit
    max_file_size_mb = models.IntegerField(default=10)  # Free tier limit
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
        limits = {
            'free': {'datasets': 5, 'sessions': 10, 'file_size': 10},
            'basic': {'datasets': 25, 'sessions': 100, 'file_size': 50},
            'pro': {'datasets': 100, 'sessions': 500, 'file_size': 200},
            'enterprise': {'datasets': -1, 'sessions': -1, 'file_size': 1000},  # -1 means unlimited
        }
        return limits.get(self.subscription_type, limits['free'])

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
    dataset = models.ForeignKey(Dataset, null=True, blank=True, on_delete=models.SET_NULL, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    spotlight_rel = models.CharField(max_length=300, null=True, blank=True)
    fitted_model = models.BinaryField(null=True, blank=True)  # Store pickled fitted model
    ordinal_predictions = models.JSONField(null=True, blank=True)  # Store pre-generated ordinal predictions
    multinomial_predictions = models.JSONField(null=True, blank=True)  # Store pre-generated multinomial predictions

    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'No User'})"

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    max_datasets = models.IntegerField()
    max_sessions = models.IntegerField()
    max_file_size_mb = models.IntegerField()
    features = models.JSONField(default=list)  # List of features
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

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
