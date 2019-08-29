"""
Project settings
"""
import sys
import django

from core.settings.base import *

sys.path.append(str(ROOT_DIR / "compsciclub_ru" / "apps"))

PROJECT_DIR = Path(__file__).parents[1]

SITE_ID = 2
ROOT_URLCONF = 'compsciclub_ru.urls'
LMS_SUBDOMAIN = None
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF
}
WSGI_APPLICATION = 'compsciclub_ru.wsgi.application'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'core.middleware.CurrentBranchMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    'international_schools.apps.Config',
    'compsciclub_ru.project_conf.ProjectConfig',  # should be the last one
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

LOCALE_PATHS = [
    str(PROJECT_DIR / "locale"),
] + LOCALE_PATHS

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(PROJECT_DIR / "templates"),
            str(APPS_DIR / "templates"),
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
                'compsciclub_ru.context_processors.get_branches',
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

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = 'development'

ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'compsciclub_ru.forms.RegistrationUniqueEmailAndUsernameForm'

ADMIN_REORDER = []


# FIXME: disable for all shared applications
MIGRATION_MODULES = {
    "core": None,
    "learning": None,
    "users": None,
    "courses": None,
    "study_programs": None,
    "gallery": None,
    "library": None,
}
