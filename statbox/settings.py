import os
from pathlib import Path
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

# Data Encryption Settings
# Use a separate encryption key for data encryption (different from SECRET_KEY)
# Generate ONCE with: python manage.py generate_encryption_key
# Store in .env file and reuse the same key (don't regenerate each time!)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', SECRET_KEY)
# Enable encryption for datasets (set to False to disable)
ENCRYPT_DATASETS = os.environ.get('ENCRYPT_DATASETS', 'False').lower() == 'true'  # Default False for development

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

# Email settings
# Supports Resend, Gmail, and other SMTP providers via environment variables
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.resend.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
# Port 465 uses SSL (SMTPS), port 587 uses TLS (STARTTLS)
# Default to SSL for port 465
if EMAIL_PORT == 465:
    EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() == 'true'
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'resend')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@statbox.com')

# Email timeout settings to prevent hanging on connection failures
EMAIL_TIMEOUT = 10  # 10 seconds timeout for SMTP connections

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
    # Allauth authentication backend
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth Account Settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'  # Allow login with username or email

# Make email verification optional when using console email backend (for development/testing)
# This allows users to register and use the app immediately when email isn't configured
if 'console' in EMAIL_BACKEND.lower():
    ACCOUNT_EMAIL_VERIFICATION = 'none'  # Skip email verification when using console backend
else:
    ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # Require email verification when email is working

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

# Customize allauth adapter to create UserProfile
ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'

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
    # 'ckeditor',  # Uncomment after installing: pip install django-ckeditor
    # 'ckeditor_uploader',  # Uncomment after installing: pip install django-ckeditor
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

# Check if CKEditor is installed (after CKEDITOR settings are defined)
try:
    import ckeditor
    INSTALLED_APPS.insert(6, 'ckeditor')
    try:
        import ckeditor_uploader
        INSTALLED_APPS.insert(7, 'ckeditor_uploader')
    except ImportError:
        pass
except ImportError:
    pass

MIDDLEWARE = [
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

