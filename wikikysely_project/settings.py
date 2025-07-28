from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('django_secret')

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    'wikikysely_project.survey',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wikikysely_project.urls'

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
                'wikikysely_project.survey.context_processors.unanswered_count',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'wikikysely_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'fi'

LANGUAGES = [
    ('fi', 'Finnish'),
    ('sv', 'Swedish'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
# Use a separate collection directory for production builds
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Allow the development server to find project level static assets
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# After logging in, redirect users to the Finnish index page instead of the
# nonexistent ``/accounts/profile/`` path provided by Django's defaults.
LOGIN_REDIRECT_URL = '/fi/'

from django.contrib.messages import constants as message_constants

# Map the ``ERROR`` level to Bootstrap's ``danger`` style so error
# notifications render correctly.
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# Social-auth settings for Wikimedia OAuth1 login
AUTHENTICATION_BACKENDS = [
    'social_core.backends.mediawiki.MediaWiki',
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_MEDIAWIKI_URL = 'https://meta.wikimedia.org/w/index.php'
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['groups']

SOCIAL_AUTH_MEDIAWIKI_KEY = os.environ.get('mediawiki_key')
SOCIAL_AUTH_MEDIAWIKI_SECRET = os.environ.get('mediawiki_secret')
SOCIAL_AUTH_MEDIAWIKI_CALLBACK = os.environ.get('mediawiki_callback')
