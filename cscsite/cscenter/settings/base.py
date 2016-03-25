"""
CS center app specific settings
"""

from unipath import Path
from core.settings.base import *

SITE_ID = 1
ROOT_URLCONF = 'cscenter.urls'
WSGI_APPLICATION = 'cscenter.wsgi.application'

BASE_DIR = Path(__file__).ancestor(2)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'users.backends.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.notifications.UnreadNotificationsCacheMiddleware',
)

INSTALLED_APPS += (
    'learning.admission',
)

# Add site specific templates
TEMPLATES[0]['DIRS'] += [BASE_DIR.child("templates")]

# FIXME: Remove after Django 1.8.4 would been released?
# https://code.djangoproject.com/ticket/24159
LOCALE_PATHS += (
    Path(BASE_DIR, "locale"),
    Path(PROJECT_DIR, "learning", "admission", "locale"),
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = Path(BASE_DIR, "newrelic.ini")
NEWRELIC_ENV = 'development'
