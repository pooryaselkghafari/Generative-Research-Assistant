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
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@statbox.com')

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/app/'
LOGOUT_REDIRECT_URL = '/'

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    # Only enable SSL redirect if SSL is actually configured
    # Set USE_SSL=True in .env when SSL certificates are set up
    USE_SSL = os.environ.get('USE_SSL', 'False').lower() == 'true'
    SECURE_SSL_REDIRECT = USE_SSL
    SESSION_COOKIE_SECURE = USE_SSL
    CSRF_COOKIE_SECURE = USE_SSL
    X_FRAME_OPTIONS = 'DENY'




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'ckeditor',  # Uncomment after installing: pip install django-ckeditor
    # 'ckeditor_uploader',  # Uncomment after installing: pip install django-ckeditor
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
        'toolbar_Custom': [
            {'name': 'document', 'items': ['Source', '-', 'Save', 'NewPage', 'Preview', 'Print', '-', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll', '-', 'Scayt']},
            {'name': 'forms', 'items': ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select', 'Button', 'ImageButton', 'HiddenField']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl', 'Language']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', 'Iframe']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks', '-', 'About']}
        ],
        'toolbar': 'Custom',
        'extraPlugins': 'colorbutton,font,justify,liststyle',
        'removePlugins': 'flash',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
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
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Allow same-origin iframes so the cleaner can load inside the modal
X_FRAME_OPTIONS = 'SAMEORIGIN'

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

