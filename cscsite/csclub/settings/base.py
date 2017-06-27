"""
CS club app specific settings
"""

from core.settings.base import *

BASE_DIR = Path(__file__).parents[1]

SITE_ID = 2
ROOT_URLCONF = 'csclub.urls'
WSGI_APPLICATION = 'csclub.wsgi.application'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'solid_i18n.middleware.SolidLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'users.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.notifications.UnreadNotificationsCacheMiddleware',  # TODO: move to notifications module
    'core.middleware.CurrentCityMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    'captcha',
    'registration',
]


SOLID_I18N_USE_REDIRECTS = False
# Redirect from /ru/... to /... if default_lang == 'ru'
SOLID_I18N_DEFAULT_PREFIX_REDIRECT = True

LOCALE_PATHS = [
    str(BASE_DIR / "locale"),
] + LOCALE_PATHS

# Template overrides
TEMPLATES[0]['DIRS'] = [str(BASE_DIR / "templates")] + TEMPLATES[0]['DIRS']
TEMPLATES[0]['OPTIONS']['context_processors'] += (
    'core.context_processors.cities',
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compsciclub.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = str(BASE_DIR / "newrelic.ini")
NEWRELIC_ENV = 'development'

# Registration and Recaptcha settings
RECAPTCHA_PUBLIC_KEY = '6Lc_7AsTAAAAAOoC9MhVSoJ6O-vILaGgDEgtLBty'
RECAPTCHA_PRIVATE_KEY = '6Lc_7AsTAAAAAJeq5ZzlUQC471py3sq404u8DYqr'
NOCAPTCHA = True
RECAPTCHA_USE_SSL = True

ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'csclub.forms.RegistrationUniqueEmailAndUsernameForm'
