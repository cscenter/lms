"""
CS center app specific settings
"""

from unipath import Path
from core.settings.base import *

BASE_DIR = Path(__file__).ancestor(2)

SITE_ID = 2
ROOT_URLCONF = 'csclub.urls'
WSGI_APPLICATION = 'csclub.wsgi.application'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'solid_i18n.middleware.SolidLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'core.notifications.UnreadNotificationsCacheMiddleware',
)

SOLID_I18N_USE_REDIRECTS = False
# Redirect from /ru/... to /... if default_lang == 'ru'
SOLID_I18N_DEFAULT_PREFIX_REDIRECT = True

# FIXME: Remove after Django 1.8.4 would been released? 
# https://code.djangoproject.com/ticket/24159
LOCALE_PATHS += (
    Path(BASE_DIR, "locale"),
)

# Template overrides
TEMPLATES[0]['DIRS'] = [BASE_DIR.child("templates")] + TEMPLATES[0]['DIRS']

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compsciclub.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = Path(BASE_DIR, "newrelic.ini")
NEWRELIC_ENV = 'development'
