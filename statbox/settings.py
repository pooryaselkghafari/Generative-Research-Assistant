import os
from pathlib import Path

# Load environment variables from .env file (if it exists)
# This allows using .env file instead of exporting variables manually
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    # Environment variables must be set manually or via system
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = []
candidate = BASE_DIR / 'static'
if candidate.exists():
    STATICFILES_DIRS.append(candidate)

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
# CSRF trusted origins (required for Django 4.0+ with HTTPS)
# Automatically set from ALLOWED_HOSTS when USE_SSL is enabled
USE_SSL = os.environ.get('USE_SSL', 'False').lower() == 'true'
if USE_SSL:
    CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host]
else:
    CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('CSRF_TRUSTED_ORIGINS') else []

# Encryption has been removed for local development

# Admin URL - Use a non-obvious path for security
# Set ADMIN_URL in .env to customize (e.g., ADMIN_URL=admin)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin').strip('/')

# Admin Security Settings
# IP Restriction: Only allow these IPs to access admin (comma-separated)
# Leave empty to disable IP restriction
ADMIN_ALLOWED_IPS = [
    ip.strip() 
    for ip in os.environ.get('ADMIN_ALLOWED_IPS', '').split(',') 
    if ip.strip()
]

# Hide admin from unauthorized visitors: Return 404 instead of 403
# This prevents attackers from knowing the admin path exists
# Only applies if ADMIN_ALLOWED_IPS is set
ADMIN_HIDE_FROM_UNAUTHORIZED = os.environ.get('ADMIN_HIDE_FROM_UNAUTHORIZED', 'True').lower() == 'true'

# Database
# Use SQLite for local development, PostgreSQL for production
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'statbox'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Stripe settings
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')


# Supabase integration settings
# Internal URL for proxy (used by supabase_proxy view)
SUPABASE_STUDIO_URL = os.environ.get('SUPABASE_STUDIO_URL', 'http://127.0.0.1:54323')
# Public URL for redirects (used by admin view)
SUPABASE_STUDIO_PUBLIC_URL = os.environ.get('SUPABASE_STUDIO_PUBLIC_URL', 'https://studio.example.com')

# Email settings
# Supports Resend API (recommended) or SMTP
# Option 1: Resend API (more reliable, no SMTP ports needed)
# Email configuration (using Django's default backend)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# Email timeout settings to prevent hanging on connection failures
EMAIL_TIMEOUT = 10  # 10 seconds timeout for SMTP connections

# Password Validation - Basic Requirements
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/app/'
LOGOUT_REDIRECT_URL = '/'

# Django Allauth Settings
SITE_ID = 1  # Required for allauth

# Allauth Configuration
AUTHENTICATION_BACKENDS = [
    # Django's default authentication backend
    'django.contrib.auth.backends.ModelBackend',
    # Allauth authentication backend (for social auth)
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth Account Settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'  # Allow login with username or email

# Email verification setting
# Set to 'mandatory' to require email verification before account activation
# Set to 'optional' to make verification optional but recommended
# Set to 'none' to skip verification (not recommended for production)
ACCOUNT_EMAIL_VERIFICATION = os.environ.get('ACCOUNT_EMAIL_VERIFICATION', 'mandatory')

ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True  # Remember user login
ACCOUNT_LOGOUT_ON_GET = True  # Logout on GET request

# Social Account Settings (Google OAuth)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'APP': {
            'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', ''),
            'key': ''
        }
    }
}

# Allauth adapters (using default adapters)
# ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'  # Removed - accounts folder not used
# SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'  # Removed - accounts folder not used

# Auto-create user profile when social account is created
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Google already verifies email

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    # Only enable SSL redirect if SSL is actually configured
    # Set USE_SSL=True in .env when SSL certificates are set up
    # USE_SSL is already defined above for CSRF_TRUSTED_ORIGINS
    SECURE_SSL_REDIRECT = USE_SSL
    SESSION_COOKIE_SECURE = USE_SSL
    CSRF_COOKIE_SECURE = USE_SSL
    # Allow same-origin iframes so the cleaner modal can load (SAMEORIGIN allows iframes from same domain)
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    # Trust X-Forwarded-Proto header from nginx (required when behind reverse proxy)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    'ckeditor',  # Rich text editor for admin
    'ckeditor_uploader',  # File upload support for CKEditor
    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'engine',
    'accounts',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CKEditor Configuration (must be before ckeditor_uploader import)
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'height': 500,
        'width': '100%',
        'external_plugin_resources': [
            ('subscription_plans', '/static/engine/ckeditor_plugins/subscription_plans/', 'plugin.js'),
        ],
        'toolbar_Custom': [
            {'name': 'document', 'items': ['Source', '-', 'Save', 'NewPage', 'Preview', 'Print', '-', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll', '-', 'Scayt']},
            {'name': 'forms', 'items': ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select', 'Button', 'ImageButton', 'HiddenField']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl', 'Language']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', 'Iframe', 'SubscriptionPlans']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks', '-', 'About']},
            ['Maximize']  # Add maximize button as standalone for easier access
        ],
        'toolbar': 'Custom',
        'extraPlugins': 'colorbutton,font,justify,liststyle,subscription_plans',
        'removePlugins': 'flash',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
        'resize_enabled': True,  # Allow manual resizing
        'resize_dir': 'vertical',  # Only vertical resizing
        'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        'extraAllowedContent': 'h3 h4 h5 h6 p blockquote pre strong em code sup sub',
        'allowedContent': True,
        'colorButton_colors': '000000,993300,333300,003300,003366,000080,333399,333333,800000,FF6600,808000,008000,008080,0000FF,666699,808080,FF0000,FF9900,99CC00,339966,33CCCC,3366FF,800080,999999,FF00FF,FFCC00,FFFF00,00FF00,00FFFF,00CCFF,9933CC,FFFFFF,FF99CC,FFCC99,FFFF99,CCFFCC,CCFFFF,99CCFF,CC99FF,FF99CC,FFCC99,FFFF99,CCFFCC,CCFFFF,99CCFF,CC99FF',
        'colorButton_enableAutomatic': False,
        'colorButton_enableMore': True,
        'fontSize_sizes': '8/8px;9/9px;10/10px;11/11px;12/12px;14/14px;16/16px;18/18px;20/20px;22/22px;24/24px;26/26px;28/28px;36/36px;48/48px;72/72px',
        'fontSize_style': {
            'element': 'span',
            'styles': {'font-size': '#(size)'},
            'overrides': [{'element': 'font', 'attributes': {'size': None}}]
        },
        'stylesSet': [
            {'name': 'Heading 1', 'element': 'h1', 'styles': {'font-size': '2.5em', 'font-weight': 'bold', 'margin': '0.67em 0'}},
            {'name': 'Heading 2', 'element': 'h2', 'styles': {'font-size': '2em', 'font-weight': 'bold', 'margin': '0.75em 0'}},
            {'name': 'Heading 3', 'element': 'h3', 'styles': {'font-size': '1.5em', 'font-weight': 'bold', 'margin': '0.83em 0'}},
            {'name': 'Heading 4', 'element': 'h4', 'styles': {'font-size': '1.17em', 'font-weight': 'bold', 'margin': '1em 0'}},
            {'name': 'Heading 5', 'element': 'h5', 'styles': {'font-size': '1em', 'font-weight': 'bold', 'margin': '1.17em 0'}},
            {'name': 'Heading 6', 'element': 'h6', 'styles': {'font-size': '0.83em', 'font-weight': 'bold', 'margin': '1.33em 0'}},
            {'name': 'Paragraph', 'element': 'p'},
            {'name': 'Code', 'element': 'code', 'styles': {'font-family': 'monospace', 'background-color': '#f5f5f5', 'padding': '2px 4px', 'border-radius': '3px'}},
            {'name': 'Blockquote', 'element': 'blockquote', 'styles': {'border-left': '4px solid #ccc', 'margin-left': '0', 'padding-left': '16px', 'font-style': 'italic'}},
        ],
    },
}

# Ensure logs directory exists and check permissions BEFORE configuring logging
import os
logs_dir = BASE_DIR / 'logs'
logs_file = logs_dir / 'django.log'
can_write_logs = False

try:
    os.makedirs(logs_dir, exist_ok=True)
    # Test if we can write to the logs directory by trying to create a test file
    test_file = logs_dir / '.test_write'
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        can_write_logs = True
    except (PermissionError, OSError):
        can_write_logs = False
except (PermissionError, OSError):
    can_write_logs = False

# Logging Configuration (conditional based on write permissions)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'engine': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Only add file handler if we can write to logs directory
if can_write_logs:
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': str(logs_file),
        'formatter': 'verbose',
    }
    # Add file handler to root and loggers
    LOGGING['root']['handlers'].append('file')
    for logger_name in ['django', 'engine', 'accounts']:
        if logger_name in LOGGING['loggers']:
            LOGGING['loggers'][logger_name]['handlers'].append('file')

# CKEditor is now included in INSTALLED_APPS above
# No need to add it dynamically since it's already in the list

MIDDLEWARE = [
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Must be before N8nAuthMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Admin security middleware (must be after AuthenticationMiddleware)
    'statbox.middleware.AdminSecurityMiddleware',
    # n8n auth middleware (must be after AuthenticationMiddleware)
    # Temporarily commented out - causing import issues
    # 'engine.middleware.n8n_auth.N8nAuthMiddleware',
]

ROOT_URLCONF = 'statbox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'engine.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'statbox.wsgi.application'

# Database configuration moved above

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Toronto'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS is defined at the top of the file with conditional check

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

