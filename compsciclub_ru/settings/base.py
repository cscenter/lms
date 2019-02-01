"""
CS club app specific settings
"""
import django

from core.settings.base import *

APP_DIR = Path(__file__).parents[1]

SITE_ID = 2
ROOT_URLCONF = 'compsciclub_ru.urls'
SUBDOMAIN_URLCONFS = {None: ROOT_URLCONF}
WSGI_APPLICATION = 'compsciclub_ru.wsgi.application'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'users.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'core.middleware.CurrentCityMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    # FIXME: create separated dir for project specific apps
    'compsciclub_ru',
    'treemenus',
    'menu_extension',
    'captcha',
    'registration',
    'international_schools.apps.Config',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

LOCALE_PATHS = [
    str(APP_DIR / "locale"),
] + LOCALE_PATHS

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(APP_DIR / "templates"),
            str(PROJECT_DIR / "templates"),
            django.__path__[0] + '/forms/templates',
        ],
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'core.context_processors.cities',
                'core.context_processors.subdomain',
            ),
            'debug': DEBUG
        }
    },
]
FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'chf0ao=9=ihflu_ln2&z+jke)*cx=k0e3mzuq+pc+x+6@vxrj9'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compsciclub.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = str(APP_DIR / "newrelic.ini")
NEWRELIC_ENV = 'development'

# Registration and Recaptcha settings
RECAPTCHA_PUBLIC_KEY = '6Lc_7AsTAAAAAOoC9MhVSoJ6O-vILaGgDEgtLBty'
RECAPTCHA_PRIVATE_KEY = '6Lc_7AsTAAAAAJeq5ZzlUQC471py3sq404u8DYqr'
NOCAPTCHA = True
RECAPTCHA_USE_SSL = True

ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'compsciclub_ru.forms.RegistrationUniqueEmailAndUsernameForm'

ADMIN_REORDER = []
