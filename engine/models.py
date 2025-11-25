from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .encrypted_fields import EncryptedCharField

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    subscription_plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        help_text="User's current subscription plan"
    )
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = EncryptedCharField(max_length=100, blank=True, null=True, help_text="Encrypted Stripe customer ID")
    stripe_subscription_id = EncryptedCharField(max_length=100, blank=True, null=True, help_text="Encrypted Stripe subscription ID")
    max_datasets = models.IntegerField(null=True, blank=True, help_text="Override plan default. Null means use plan's max_datasets. Use -1 for unlimited.")
    max_sessions = models.IntegerField(null=True, blank=True, help_text="Override plan default. Null means use plan's max_sessions. Use -1 for unlimited.")
    max_file_size_mb = models.IntegerField(null=True, blank=True, help_text="Override plan default. Null means use plan's max_file_size_mb. Use -1 for unlimited.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        plan_name = self.subscription_plan.name if self.subscription_plan else "No Plan"
        return f"{self.user.username} - {plan_name}"
    
    @property
    def subscription_type(self):
        """Backward compatibility: return plan name or 'free'"""
        if self.subscription_plan:
            return self.subscription_plan.name.lower().replace(' ', '_')
        return 'free'
    
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
        """Get limits from subscription plan or use defaults"""
        if self.subscription_plan:
            return {
                'datasets': self.max_datasets if self.max_datasets is not None else self.subscription_plan.max_datasets,
                'sessions': self.max_sessions if self.max_sessions is not None else self.subscription_plan.max_sessions,
                'file_size': self.max_file_size_mb if self.max_file_size_mb is not None else self.subscription_plan.max_file_size_mb,
            }
        # Fallback to free tier defaults
        return {
            'datasets': 5,
            'sessions': 10,
            'file_size': 10,
        }
    
    def get_ai_features(self):
        """Get AI features - returns default disabled state"""
        return {
            'ai_enabled': False,
            'model_type': None,
            'rag_enabled': False,
            'fine_tuning_enabled': False,
        }

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

class SubscriptionPlan(models.Model):
    """
    Unified subscription plan model that combines pricing, features, limits, and workflow configuration.
    Replaces the previous SubscriptionTierSettings and SubscriptionPlan separation.
    """
    # Basic Information
    name = models.CharField(max_length=50, unique=True, help_text="Plan name (e.g., 'Free', 'Pro', 'Enterprise')")
    description = models.TextField(help_text="Description of this subscription plan")
    is_active = models.BooleanField(default=True, help_text="Whether this plan is available for purchase")
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Monthly price in USD")
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Yearly price in USD (usually discounted)")
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True, help_text="Stripe Price ID for monthly billing")
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True, help_text="Stripe Price ID for yearly billing")
    
    # Features
    features = models.JSONField(default=list, help_text="List of feature strings displayed to users (e.g., ['AI Interpretation', 'RAG Support'])")
    ai_features = models.JSONField(default=list, help_text="AI-specific features for this plan")
    
    # Resource Limits
    max_datasets = models.IntegerField(default=5, help_text="Maximum number of datasets. Use -1 for unlimited.")
    max_sessions = models.IntegerField(default=10, help_text="Maximum number of analysis sessions. Use -1 for unlimited.")
    max_file_size_mb = models.IntegerField(default=10, help_text="Maximum file size in MB. Use -1 for unlimited.")
    
    # Workflow Configuration
    workflow_template = models.ForeignKey(
        'AgentTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscription_plans',
        help_text="Agent Template (n8n workflow) used for chatbot access. Users without a workflow will see an upgrade message."
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price_monthly']
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
    
    def __str__(self):
        return self.name
    
    def get_limits(self):
        """Get resource limits for this plan"""
        return {
            'datasets': self.max_datasets,
            'sessions': self.max_sessions,
            'file_size': self.max_file_size_mb,
        }

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    stripe_payment_intent_id = EncryptedCharField(max_length=100, help_text="Encrypted Stripe payment intent ID")
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


class SiteSettings(models.Model):
    """Global site settings including Google Analytics and other tracking codes"""
    google_analytics_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Google Analytics tracking ID (e.g., G-8FHJC3M9SD). Leave empty to disable."
    )
    google_analytics_code = models.TextField(
        blank=True,
        null=True,
        help_text="Custom Google Analytics code (full script tags). If provided, this will be used instead of google_analytics_id."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable Google Analytics tracking"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one SiteSettings instance exists
        if not self.pk:
            # Delete any existing instances
            SiteSettings.objects.exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the active site settings (singleton pattern)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class N8nWorkflow(models.Model):
    """
    Local cache of n8n workflows so admins can map them to chatbots/subscriptions.
    The workflow ID in n8n can be a UUID-like string, so store as CharField.
    """
    workflow_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="n8n workflow ID (string)."
    )
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)
    version_id = models.CharField(max_length=100, blank=True)
    webhook_id = models.CharField(max_length=100, blank=True)
    test_url = models.URLField(blank=True)
    production_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True, help_text="Raw workflow payload for reference")
    n8n_created_at = models.DateTimeField(null=True, blank=True)
    n8n_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "n8n Workflow"
        verbose_name_plural = "n8n Workflows"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (ID: {self.workflow_id})"


class AgentTemplate(models.Model):
    """
    Represents an n8n workflow template that can be used by the chatbot.
    
    Each template links a chatbot mode or use case to a specific n8n webhook workflow.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
    ]
    
    VISIBILITY_CHOICES = [
        ('internal', 'Internal Only'),
        ('customer_facing', 'Customer Facing'),
    ]
    
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique name for this agent template (e.g., 'research_agent', 'sop_agent')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this agent template does"
    )
    n8n_webhook_url = models.URLField(
        max_length=500,
        help_text="Full URL to the n8n webhook endpoint (e.g., http://localhost:5678/webhook/abc123)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Template status: active (usable), inactive (disabled), draft (in development)"
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='customer_facing',
        help_text="Who can use this template: internal (staff only) or customer_facing (all users)"
    )
    mode_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Optional: Chatbot mode key that maps to this template (e.g., 'research_agent'). If set, this template will be used when user selects this mode."
    )
    workflow = models.ForeignKey(
        'N8nWorkflow',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_templates',
        help_text="Optional: Link this template to a synced n8n workflow for easier management."
    )
    default_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default parameters to send to n8n webhook (JSON object)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_agent_templates',
        help_text="User who created this template"
    )
    
    class Meta:
        verbose_name = "Agent Template"
        verbose_name_plural = "Agent Templates"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['mode_key']),
            models.Index(fields=['visibility']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def is_usable(self):
        """Check if template is active and ready to use."""
        return self.status == 'active'
    
    def can_be_used_by(self, user):
        """Check if user can use this template."""
        if self.visibility == 'internal' and not user.is_staff:
            return False
        return self.is_usable()


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
        ('privacy', 'Privacy Compliance Tests'),
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


class AIFineTuningFile(models.Model):
    """
    Files uploaded for AI fine-tuning.
    
    Stores metadata about files used for fine-tuning the AI model,
    including training data, validation data, prompt templates, etc.
    """
    FILE_TYPE_TRAINING = 'training'
    FILE_TYPE_VALIDATION = 'validation'
    FILE_TYPE_PROMPT = 'prompt'
    FILE_TYPE_SYSTEM = 'system'
    FILE_TYPE_OTHER = 'other'
    
    FILE_TYPE_CHOICES = [
        (FILE_TYPE_TRAINING, 'Training Data'),
        (FILE_TYPE_VALIDATION, 'Validation Data'),
        (FILE_TYPE_PROMPT, 'Prompt Template'),
        (FILE_TYPE_SYSTEM, 'System Instructions'),
        (FILE_TYPE_OTHER, 'Other'),
    ]
    
    name = models.CharField(
        max_length=255,
        help_text="Name/description of the file"
    )
    file = models.FileField(
        upload_to='ai_finetuning/files/',
        help_text="File to use for fine-tuning"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this file contains"
    )
    file_type = models.CharField(
        max_length=50,
        choices=FILE_TYPE_CHOICES,
        default=FILE_TYPE_TRAINING,
        help_text="Type of file"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this file is currently active",
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_finetuning_files',
        db_index=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "AI Fine-tuning File"
        verbose_name_plural = "AI Fine-tuning Files"
        indexes = [
            models.Index(fields=['-uploaded_at', 'is_active']),
            models.Index(fields=['file_type', 'is_active']),
        ]
    
    def __str__(self) -> str:
        """Return string representation of the file."""
        return f"{self.name} ({self.get_file_type_display()})"


class AIFineTuningCommand(models.Model):
    """
    Commands sent to fine-tune the AI model.
    
    Tracks all fine-tuning operations including their status,
    results, and associated files.
    """
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    COMMAND_TYPE_FINE_TUNE = 'fine_tune'
    COMMAND_TYPE_UPDATE_PROMPT = 'update_prompt'
    COMMAND_TYPE_ADD_CONTEXT = 'add_context'
    COMMAND_TYPE_TEST_MODEL = 'test_model'
    COMMAND_TYPE_RESET_MODEL = 'reset_model'
    COMMAND_TYPE_OTHER = 'other'
    
    COMMAND_TYPE_CHOICES = [
        (COMMAND_TYPE_FINE_TUNE, 'Fine-tune Model'),
        (COMMAND_TYPE_UPDATE_PROMPT, 'Update System Prompt'),
        (COMMAND_TYPE_ADD_CONTEXT, 'Add Context Data'),
        (COMMAND_TYPE_TEST_MODEL, 'Test Model'),
        (COMMAND_TYPE_RESET_MODEL, 'Reset Model'),
        (COMMAND_TYPE_OTHER, 'Other'),
    ]
    
    command_type = models.CharField(
        max_length=50,
        choices=COMMAND_TYPE_CHOICES,
        default=COMMAND_TYPE_FINE_TUNE,
        help_text="Type of command",
        db_index=True
    )
    description = models.TextField(
        help_text="Description of what this command does"
    )
    command_data = models.JSONField(
        default=dict,
        help_text="JSON data for the command (e.g., parameters, file IDs, etc.)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    result = models.TextField(
        blank=True,
        help_text="Result or error message from command execution"
    )
    files = models.ManyToManyField(
        AIFineTuningFile,
        blank=True,
        related_name='commands',
        help_text="Files associated with this command"
    )
    provider = models.ForeignKey(
        'AIProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commands',
        help_text="AI provider to use for this command (uses default if not specified)",
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_finetuning_commands',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "AI Fine-tuning Command"
        verbose_name_plural = "AI Fine-tuning Commands"
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['command_type', 'status']),
        ]
    
    def __str__(self) -> str:
        """Return string representation of the command."""
        date_str = self.created_at.strftime('%Y-%m-%d %H:%M')
        return f"{self.get_command_type_display()} - {self.status} ({date_str})"


class Ticket(models.Model):
    """
    Bug report ticket system for users to report issues.
    Admins can view and manage tickets.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admins")
    admin_response = models.TextField(blank=True, help_text="Response visible to user")
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets',
        limit_choices_to={'is_staff': True}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.title} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        """Auto-set resolved_at when status changes to resolved/closed"""
        if self.status in ('resolved', 'closed') and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        elif self.status not in ('resolved', 'closed'):
            self.resolved_at = None
        super().save(*args, **kwargs)


class AIProvider(models.Model):
    """
    AI Provider configuration for fine-tuning operations.
    
    Stores API keys, provider settings, and authentication details
    for connecting to AI service providers (OpenAI, Anthropic, etc.).
    """
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic Claude'),
        ('custom', 'Custom API'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name for this provider configuration (e.g., 'Production OpenAI', 'Development Claude')"
    )
    provider_type = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='openai',
        help_text="Type of AI provider"
    )
    api_key = EncryptedCharField(
        max_length=500,
        help_text="API key for authentication (encrypted)"
    )
    api_base_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Base URL for API (optional, uses provider default if not set)"
    )
    base_model = models.CharField(
        max_length=100,
        default='gpt-3.5-turbo',
        help_text="Base model identifier (e.g., 'gpt-3.5-turbo', 'claude-3-opus')"
    )
    fine_tuned_model_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="ID of the fine-tuned model (if available)"
    )
    organization_id = EncryptedCharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Organization ID (for OpenAI, encrypted)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this provider is currently active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default provider"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_providers',
        help_text="User who created this configuration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_tested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this provider was successfully tested"
    )
    test_status = models.CharField(
        max_length=20,
        choices=[
            ('untested', 'Untested'),
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        default='untested',
        help_text="Status of last connection test"
    )
    test_message = models.TextField(
        blank=True,
        help_text="Message from last connection test"
    )
    
    class Meta:
        ordering = ['-is_default', '-is_active', 'name']
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"
        indexes = [
            models.Index(fields=['provider_type', 'is_active']),
            models.Index(fields=['is_default', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_provider'
            )
        ]
    
    def __str__(self):
        """String representation with safe encoding."""
        try:
            status = "✓" if self.is_active else "✗"
            default = " [DEFAULT]" if self.is_default else ""
            provider_type = self.get_provider_type_display() if hasattr(self, 'provider_type') else 'Unknown'
            name = self.name if hasattr(self, 'name') else 'Unnamed'
            return f"{status} {name} ({provider_type}){default}"
        except Exception:
            # Fallback if there's any error (e.g., encoding, missing fields)
            return f"AIProvider #{self.pk if hasattr(self, 'pk') else '?'}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default provider exists."""
        if self.is_default:
            # Unset other default providers
            AIProvider.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_provider(cls):
        """Get the active default provider or first active provider."""
        try:
            return cls.objects.filter(is_active=True, is_default=True).first() or \
                   cls.objects.filter(is_active=True).first()
        except cls.DoesNotExist:
            return None


class AIFineTuningTemplate(models.Model):
    """
    JSON templates for AI fine-tuning commands.
    
    Stores reusable JSON templates that users can select and edit
    when creating fine-tuning commands.
    """
    name = models.CharField(
        max_length=255,
        help_text="Name of the template"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this template is for"
    )
    command_type = models.CharField(
        max_length=50,
        choices=AIFineTuningCommand.COMMAND_TYPE_CHOICES,
        help_text="Command type this template is for"
    )
    template_data = models.JSONField(
        default=dict,
        help_text="JSON template data"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active",
        db_index=True
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default template for this command type"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_finetuning_templates',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['command_type', 'name']
        verbose_name = "AI Fine-tuning Template"
        verbose_name_plural = "AI Fine-tuning Templates"
        indexes = [
            models.Index(fields=['command_type', 'is_active']),
            models.Index(fields=['is_default', 'command_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['command_type'],
                condition=models.Q(is_default=True),
                name='unique_default_per_command_type'
            )
        ]
    
    def __str__(self) -> str:
        """Return string representation of the template."""
        return f"{self.name} ({self.get_command_type_display()})"
