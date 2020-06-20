"""
Project settings
"""
import logging

import django

import environ

from core.settings.base import *

env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

PROJECT_DIR = Path(__file__).parents[1]

SITE_ID = 1

DEBUG = MODELTRANSLATION_DEBUG = env.bool('DEBUG', default=False)

WSGI_APPLICATION = 'compscicenter_ru.wsgi.application'
ROOT_URLCONF = 'compscicenter_ru.urls'
# FIXME: move to the SiteConfiguration model
LMS_SUBDOMAIN = 'my'
RESTRICT_LOGIN_TO_LMS = True
REVERSE_TO_LMS_URL_NAMESPACES = ('staff', 'study', 'teaching', 'projects',
                                 'surveys', 'library', 'admission', 'auth',
                                 'courses')
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
    LMS_SUBDOMAIN: 'lms.urls',
}

STATIC_ROOT = env.str('DJANGO_STATIC_ROOT', default=str(ROOT_DIR / "static"))
FILE_UPLOAD_DIRECTORY_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_DIRECTORY_PERMISSIONS', default=0o755)
FILE_UPLOAD_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_PERMISSIONS', default=0o664)

# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db_url(var="DATABASE_URL")
}


# Don't bind course lookup with `request.site` in CourseURLParamsMixin
COURSE_FRIENDLY_URL_USE_SITE = False

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'core.middleware.BranchViewMiddleware',
    'subdomains.middleware.SubdomainURLRoutingMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'core.middleware.RedirectMiddleware',
]
INSTALLED_APPS += [
    'dbbackup',
    'compscicenter_ru',
    'lms',
    'menu',
    'post_office',
    'django_jinja',
    'projects.apps.ProjectsConfig',
    'stats.apps.StatisticsConfig',
    'admission.apps.AdmissionConfig',
    'application.apps.ApplicationConfig',
    'staff',
    'surveys.apps.SurveysConfig',
    'online_courses.apps.Config',
    'info_blocks.apps.InfoBlocksConfig',
    'publications.apps.PublicationsConfig',
    'announcements.apps.AnnouncementsConfig',
    'faq.apps.FAQConfig',
    'ckeditor',
    'ckeditor_uploader',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    },
    'social_networks': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(ROOT_DIR / ".cache")
    }
}

REDIS_PASSWORD = env.str('REDIS_PASSWORD', default=None)
REDIS_HOST = env.str('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = env.int('REDIS_PORT', default=6379)
RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
    'high': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
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
THUMBNAIL_REDIS_PORT = REDIS_PORT
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD

# Oauth settings for getting access to login from Yandex.Passport
# Note: Application is managed by `contest@compscicenter.ru` yandex account
SOCIAL_AUTH_YANDEXRU_KEY = env.str('SOCIAL_AUTH_YANDEXRU_KEY')
SOCIAL_AUTH_YANDEXRU_SECRET = env.str('SOCIAL_AUTH_YANDEXRU_SECRET')
# Prevent calling pipeline for this backend
SOCIAL_AUTH_YANDEXRU_PIPELINE = []


# Monitoring
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("SENTRY_LOG_LEVEL", default=logging.INFO)
NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = env.str('NEWRELIC_ENV', default='production')

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
            str(PROJECT_DIR / "jinja2"),
            django.__path__[0] + '/forms/jinja2',
            str(ROOT_DIR / "lms" / "jinja2"),
            str(SHARED_APPS_DIR / "surveys" / "jinja2"),
            # svg inline support
            str(ASSETS_ROOT / "v2" / "dist" / "img"),
        ],
        "NAME": "jinja2",
        "OPTIONS": {
            "match_extension": None,
            "match_regex": r"^(?!admin/).*",
            "filters": {
                "markdown": "core.jinja2.filters.markdown",
                "pluralize": "core.jinja2.filters.pluralize",
                "with_classes": "core.jinja2.filters.with_classes",
                "youtube_video_id": "core.jinja2.filters.youtube_video_id",
                "as_survey": "surveys.jinja2_filters.render_form",
            },
            "constants": {
                "CSRF_COOKIE_NAME": CSRF_COOKIE_NAME,
                "SENTRY_DSN": SENTRY_DSN,
            },
            "globals": {
                "messages": "core.jinja2.globals.messages",
                "get_menu": "core.jinja2.globals.generate_menu",
                "crispy": "core.jinja2.globals.crispy",
                "pagination": "core.jinja2.globals.pagination",
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
                "core.jinja2.ext.SpacelessExtension"
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
            str(SHARED_APPS_DIR / "admission" / "templates"),
            str(SHARED_APPS_DIR / "staff" / "templates"),
            str(SHARED_APPS_DIR / "templates"),
            django.__path__[0] + '/forms/templates',
        ],
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                # FIXME: this setting overrides `APP_DIRS` behavior! WTF?
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
                'core.context_processors.subdomain',
                'core.context_processors.js_config',
            ),
            'debug': DEBUG
        }
    },
]
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

LOCALE_PATHS += [
    str(PROJECT_DIR / "locale"),
    str(SHARED_APPS_DIR / "projects" / "locale"),
    str(SHARED_APPS_DIR / "admission" / "locale"),
    str(SHARED_APPS_DIR / "surveys" / "locale"),
]

SECRET_KEY = env('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compscicenter.ru"])


# Email settings
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'
EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=465)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

HASHIDS_SALT = env.str('HASHIDS_SALT')

YANDEX_DISK_USERNAME = env.str('YANDEX_DISK_USERNAME')
YANDEX_DISK_PASSWORD = env.str('YANDEX_DISK_PASSWORD')

YANDEX_DISK_CLIENT_ID = env.str('YANDEX_DISK_CLIENT_ID')
YANDEX_DISK_CLIENT_SECRET = env.str('YANDEX_DISK_CLIENT_SECRET')
YANDEX_DISK_ACCESS_TOKEN = env.str('YANDEX_DISK_ACCESS_TOKEN')
YANDEX_DISK_REFRESH_TOKEN = env.str('YANDEX_DISK_REFRESH_TOKEN')


# s3boto3.S3Boto3Storage: all files will inherit the bucket’s ACL
AWS_DEFAULT_ACL = None

AWS_SES_ACCESS_KEY_ID = env.str('AWS_SES_ACCESS_KEY_ID')
AWS_SES_SECRET_ACCESS_KEY = env.str('AWS_SES_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = env.str('AWS_SES_REGION_NAME', default='eu-west-1')
AWS_SES_REGION_ENDPOINT = env.str('AWS_SES_REGION_ENDPOINT', default='email.eu-west-1.amazonaws.com')
POST_OFFICE = {
    'BACKENDS': {
        'ses': 'django.core.mail.backends.console.EmailBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}


# "ldap:///"
LDAP_CLIENT_URI = env.str('LDAP_CLIENT_URI', default="ldap://review.compscicenter.ru:389")
# Domain Component suffix for distinguished name (or DN)
# FIXME: move to the SiteConfiguration
LDAP_DB_SUFFIX = env.str('LDAP_DB_SUFFIX', default="dc=review,dc=compscicenter,dc=ru")
LDAP_CLIENT_USERNAME = env.str('LDAP_CLIENT_USERNAME', default="admin")
LDAP_CLIENT_PASSWORD = env.str('LDAP_CLIENT_PASSWORD')
LDAP_TLS_TRUSTED_CA_CERT_FILE = env.str('LDAP_TLS_TRUSTED_CA_CERT_FILE', default=str(PROJECT_DIR / "LDAPTrustedCA.crt"))
LDAP_SYNC_PASSWORD = env.bool('LDAP_SYNC_PASSWORD', default=True)


GERRIT_API_URI = env.str('GERRIT_API_URI', default="https://review.compscicenter.ru/a/")
GERRIT_CLIENT_USERNAME = env.str('GERRIT_CLIENT_USERNAME', default="admin")
GERRIT_CLIENT_HTTP_PASSWORD = env.str('GERRIT_CLIENT_HTTP_PASSWORD')

# Default keys are taken from https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")
RECAPTCHA_USE_SSL = True

# Stub
ADMIN_REORDER = []

SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_DOMAIN = env.str('DJANGO_SESSION_COOKIE_DOMAIN', default='.compscicenter.ru')
SESSION_COOKIE_NAME = env.str('DJANGO_SESSION_COOKIE_NAME', default='cscsessionid')
SESSION_COOKIE_SAMESITE = env.str('DJANGO_SESSION_COOKIE_SAMESITE', default=None)
CSRF_COOKIE_SECURE = env.bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_DOMAIN = env.str('DJANGO_CSRF_COOKIE_DOMAIN', default='.compscicenter.ru')
CSRF_COOKIE_NAME = env.str('DJANGO_CSRF_COOKIE_NAME', default='csrftoken')


# Registration partially used on my.* (see `learning/invitation`)
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
ACCOUNT_ACTIVATION_DAYS = 1
ACTIVATION_EMAIL_SUBJECT = 'emails/activation_email_subject.txt'
ACTIVATION_EMAIL_BODY = 'emails/activation_email_body.txt'

