"""
Project settings
"""
import sys
import django

import environ

from core.settings.base import *

sys.path.append(str(ROOT_DIR / "compsciclub_ru" / "apps"))

env = environ.Env()
environ.Env.read_env()  # reading .env file

SITE_ID = 2

DEBUG = MODELTRANSLATION_DEBUG = env.bool('DEBUG', default=False)

PROJECT_DIR = Path(__file__).parents[1]

FILE_UPLOAD_DIRECTORY_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_DIRECTORY_PERMISSIONS', default=0o755)
FILE_UPLOAD_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_PERMISSIONS', default=0o664)

# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db_url(var="DATABASE_URL")
}

ROOT_URLCONF = 'compsciclub_ru.urls'
RESTRICT_LOGIN_TO_LMS = True
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
    'info_blocks.apps.InfoBlocksConfig',
    'compsciclub_ru.project_conf.ProjectConfig',  # should be the last one
]

REDIS_PASSWORD = env.str('REDIS_PASSWORD', default=None)
REDIS_HOST = env.str('REDIS_HOST', default='127.0.0.1')
RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
    'high': {
        'HOST': REDIS_HOST,
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
}


# https://sorl-thumbnail.readthedocs.io/en/latest/reference/settings.html
THUMBNAIL_DEBUG = DEBUG
THUMBNAIL_DUMMY = True
THUMBNAIL_PRESERVE_FORMAT = True
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_REDIS_HOST = REDIS_HOST
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD


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
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
            str(PROJECT_DIR / "jinja2"),
            django.__path__[0] + '/forms/jinja2',
            str(ROOT_DIR / "lms" / "jinja2"),
        ],
        "NAME": "jinja2",
        "OPTIONS": {
            "match_extension": None,
            "match_regex": r"^(?!admin/).*",
            "filters": {
                "markdown": "core.jinja2.filters.markdown",
                "pluralize": "core.jinja2.filters.pluralize",
                "with_classes": "core.jinja2.filters.with_classes",
            },
            "globals": {
                "messages": "core.jinja2.globals.messages",
                "get_menu": "core.jinja2.globals.generate_menu",
                "crispy": "core.jinja2.globals.crispy",
                "get_branches": "compsciclub_ru.context_processors.get_branches",
            },
            "extensions": [
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "jinja2.ext.with_",
                "jinja2.ext.i18n",
                "jinja2.ext.autoescape",
                "django_jinja.builtins.extensions.CsrfExtension",
                "django_jinja.builtins.extensions.CacheExtension",
                "django_jinja.builtins.extensions.TimezoneExtension",
                "django_jinja.builtins.extensions.StaticFilesExtension",
                "django_jinja.builtins.extensions.DjangoFiltersExtension",
                "webpack_loader.contrib.jinja2ext.WebpackExtension",
                "core.jinja2.ext.UrlExtension",
            ],
            "bytecode_cache": {
                "name": "default",
                "backend": "django_jinja.cache.BytecodeCache",
                "enabled": False,
            },
            "newstyle_gettext": True,
            "autoescape": False,
            "auto_reload": DEBUG,
            "translation_engine": "django.utils.translation",
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(PROJECT_DIR / "templates"),
            str(SHARED_APPS_DIR / "templates"),
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

SECRET_KEY = env('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compsciclub.ru"])

# Email settings
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compsciclub.ru'
EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=465)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = env.str('NEWRELIC_ENV', default='production')

HASHIDS_SALT = env.str('HASHIDS_SALT')

YANDEX_DISK_USERNAME = env.str('YANDEX_DISK_USERNAME')
YANDEX_DISK_PASSWORD = env.str('YANDEX_DISK_PASSWORD')

# Default keys are taken from https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")
RECAPTCHA_USE_SSL = True

ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'compsciclub_ru.forms.RegistrationUniqueEmailAndUsernameForm'

ADMIN_REORDER = []

SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_DOMAIN = env.str('DJANGO_SESSION_COOKIE_DOMAIN', default=None)
SESSION_COOKIE_NAME = env.str('DJANGO_SESSION_COOKIE_NAME', default='sessionid')
CSRF_COOKIE_SECURE = env.bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_DOMAIN = env.str('DJANGO_CSRF_COOKIE_DOMAIN', default=None)
CSRF_COOKIE_NAME = env.str('DJANGO_CSRF_COOKIE_NAME', default='csrftoken')

MIGRATION_MODULES = {
    "core": None,
    "courses": None,
    "htmlpages": None,
    "learning": None,
    "tasks": None,
    "gallery": None,
    "notifications": None,
    "library": None,
    "study_programs": None,
    "users": None,
}
