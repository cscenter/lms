import logging
import django
import environ

from core.settings.base import *

env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

SITE_ID = env.str('SITE_ID', default=None)

DEBUG = MODELTRANSLATION_DEBUG = env.bool('DEBUG', default=False)

RESTRICT_LOGIN_TO_LMS = True
REVERSE_TO_LMS_URL_NAMESPACES = ('staff', 'study', 'teaching', 'projects',
                                 'files', 'surveys', 'library', 'admission',
                                 'auth', 'courses')

# Default scheme for `core.urls.reverse`
DEFAULT_URL_SCHEME = env.str("REVERSE_URL_SCHEME", default="https")

SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True)

# Upload Settings
USE_S3_FOR_UPLOAD = env.bool('UPLOAD_USE_S3', default=False)
AWS_DEFAULT_ACL = None  # All files will inherit the bucket’s ACL
if USE_S3_FOR_UPLOAD:
    DEFAULT_FILE_STORAGE = 'files.storage.PublicMediaS3Storage'
    AWS_PUBLIC_MEDIA_LOCATION = 'media'
    PRIVATE_FILE_STORAGE = 'files.storage.PrivateMediaS3Storage'
    AWS_PRIVATE_MEDIA_LOCATION = 'private'
    AWS_S3_ACCESS_KEY_ID = env.str('AWS_S3_ACCESS_KEY_ID')
    AWS_S3_SECRET_ACCESS_KEY = env.str('AWS_S3_SECRET_ACCESS_KEY')
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_STORAGE_BUCKET_NAME = env.str('AWS_STORAGE_BUCKET_NAME', default='lms-vault')
    AWS_S3_REGION_NAME = 'eu-central-1'
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_PUBLIC_MEDIA_LOCATION}/'
else:
    FILE_UPLOAD_DIRECTORY_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_DIRECTORY_PERMISSIONS', default=0o755)
    FILE_UPLOAD_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_PERMISSIONS', default=0o664)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = env.str('DJANGO_PUBLIC_MEDIA_ROOT')
    # Resolve relative paths as relative to the ROOT_DIR
    if MEDIA_ROOT.startswith('.'):
        MEDIA_ROOT = str(ROOT_DIR.joinpath(MEDIA_ROOT).resolve())
    MEDIA_URL = '/media/'
    PRIVATE_FILE_STORAGE = 'files.storage.PrivateFileSystemStorage'
    PRIVATE_MEDIA_ROOT = env.str('DJANGO_PRIVATE_MEDIA_ROOT')
    PRIVATE_MEDIA_URL = '/media/private/'

# Static Files Settings
STATIC_ROOT = env.str('DJANGO_STATIC_ROOT', default=str(ROOT_DIR / "static"))
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'files.storage.FixedCompressedManifestStaticFilesStorage'

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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

REDIS_PASSWORD = env.str('REDIS_PASSWORD', default=None)
REDIS_HOST = env.str('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = env.int('REDIS_PORT', default=6379)
REDIS_DB_INDEX = env.int('REDIS_DB_INDEX', default=SITE_ID)
REDIS_SSL = env.bool('REDIS_SSL', default=True)
RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': REDIS_DB_INDEX,
        'PASSWORD': REDIS_PASSWORD,
        'SSL': REDIS_SSL,
    },
    'high': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': REDIS_DB_INDEX,
        'PASSWORD': REDIS_PASSWORD,
        'SSL': REDIS_SSL
    },
}


# https://sorl-thumbnail.readthedocs.io/en/latest/reference/settings.html
THUMBNAIL_DEBUG = DEBUG
THUMBNAIL_DUMMY = True
THUMBNAIL_PRESERVE_FORMAT = True
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_REDIS_HOST = REDIS_HOST
THUMBNAIL_REDIS_PORT = REDIS_PORT
THUMBNAIL_REDIS_DB = REDIS_DB_INDEX
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD
THUMBNAIL_REDIS_SSL = REDIS_SSL

# Monitoring
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("SENTRY_LOG_LEVEL", default=logging.INFO)

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
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

SECRET_KEY = env('DJANGO_SECRET_KEY')

# Email settings
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = env.str('DJANGO_EMAIL_ADDRESS')
EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=465)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

HASHIDS_SALT = env.str('HASHIDS_SALT')

YANDEX_DISK_USERNAME = env.str('YANDEX_DISK_USERNAME')
YANDEX_DISK_PASSWORD = env.str('YANDEX_DISK_PASSWORD')
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/"


# Default keys are taken from https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")
RECAPTCHA_USE_SSL = True

# Stub
ADMIN_REORDER = []

SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_DOMAIN = env.str('DJANGO_SESSION_COOKIE_DOMAIN', default=None)
SESSION_COOKIE_NAME = env.str('DJANGO_SESSION_COOKIE_NAME', default='sessionid')
SESSION_COOKIE_SAMESITE = env.str('DJANGO_SESSION_COOKIE_SAMESITE', default=None)
CSRF_COOKIE_SECURE = env.bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_DOMAIN = env.str('DJANGO_CSRF_COOKIE_DOMAIN', default=None)
CSRF_COOKIE_NAME = env.str('DJANGO_CSRF_COOKIE_NAME', default='csrftoken')
