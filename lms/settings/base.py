import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import environ
import pytz

import django

env = environ.Env()
# Try to read .env file, if it's not present, assume that application
# is deployed to production and skip reading the file
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))


ROOT_DIR = Path(__file__).parents[3]
SHARED_APPS_DIR = ROOT_DIR / "apps"

SITE_ID = env.str('SITE_ID', default=None)

DEBUG = MODELTRANSLATION_DEBUG = env.bool('DEBUG', default=False)

RESTRICT_LOGIN_TO_LMS = True
REVERSE_TO_LMS_URL_NAMESPACES = ('staff', 'study', 'teaching', 'projects',
                                 'files', 'surveys', 'library', 'admission',
                                 'auth', 'courses', 'learning-api')

# Default scheme for `core.urls.reverse`
DEFAULT_URL_SCHEME = env.str("REVERSE_URL_SCHEME", default="https")
LMS_SUBDOMAIN: Optional[str] = None

SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_DOMAIN = env.str('DJANGO_SESSION_COOKIE_DOMAIN', default=None)
SESSION_COOKIE_NAME = env.str('DJANGO_SESSION_COOKIE_NAME', default='sessionid')
SESSION_COOKIE_SAMESITE = env.str('DJANGO_SESSION_COOKIE_SAMESITE', default=None)
CSRF_COOKIE_SECURE = env.bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_DOMAIN = env.str('DJANGO_CSRF_COOKIE_DOMAIN', default=None)
CSRF_COOKIE_NAME = env.str('DJANGO_CSRF_COOKIE_NAME', default='csrftoken')

# Upload Settings
DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int('DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE', default=2621440)
USE_CLOUD_STORAGE = env.bool('USE_CLOUD_STORAGE', default=True)
AWS_DEFAULT_ACL: Optional[str] = None  # All files will inherit the bucket’s ACL
if USE_CLOUD_STORAGE:
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
DJANGO_ASSETS_ROOT = ROOT_DIR / "assets"
WEBPACK_ASSETS_ROOT = Path(env.str('WEBPACK_ASSETS_ROOT'), default=DJANGO_ASSETS_ROOT).resolve()
STATICFILES_DIRS = [
    str(DJANGO_ASSETS_ROOT),
    str(WEBPACK_ASSETS_ROOT),
]
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STATIC_ROOT = env.str('DJANGO_STATIC_ROOT', default=str(ROOT_DIR / "static"))
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'files.storage.CompressedManifestStaticFilesStorage'
STATIC_COMPRESS_METHODS = ["gz+zlib"]

WEBPACK_ENVIRONMENT = env.str('WEBPACK_ENVIRONMENT', default="prod")
WEBPACK_LOADER = {
    'V1': {
        'BUNDLE_DIR_NAME': f'v1/dist/{WEBPACK_ENVIRONMENT}/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(WEBPACK_ASSETS_ROOT / "v1" / "dist" / WEBPACK_ENVIRONMENT / "webpack-stats-v1.json"),
    },
    'V2': {
        'BUNDLE_DIR_NAME': f'v2/dist/{WEBPACK_ENVIRONMENT}/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(WEBPACK_ASSETS_ROOT / "v2" / "dist" / WEBPACK_ENVIRONMENT / "webpack-stats-v2.json"),
    }
}

# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db_url(var="DATABASE_URL")
}


MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    # EN language is not supported at this moment anyway
    'core.middleware.HardCodedLocaleMiddleware',
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

ESTABLISHED = 2011

# Template customization
FAVICON_PATH = 'v1/img/center/favicon.png'
LOGO_PATH = 'v1/img/center/logo.svg'
# Provide zero value to disable counter rendering
YANDEX_METRIKA_ID = env.int("YANDEX_METRIKA_ID", default=None)

DJANGO_ROOT_DIR = Path(django.__file__).parent
TEMPLATES: List[Dict[str, Any]] = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
            str(DJANGO_ROOT_DIR / "forms" / "jinja2"),
            str(ROOT_DIR / "lms" / "jinja2"),
        ],
        "NAME": "jinja2",
        "OPTIONS": {
            "match_extension": None,
            "match_regex": r"^(?!admin/|django/).*",
            "filters": {
                "markdown": "core.jinja2.filters.markdown",
                "pluralize": "core.jinja2.filters.pluralize",
                "thumbnail": "core.jinja2.filters.thumbnail",
                "with_classes": "core.jinja2.filters.with_classes",
                "youtube_video_id": "core.jinja2.filters.youtube_video_id",
                "date_soon_css": "core.jinja2.filters.date_soon_css",
                "naturalday": "django.contrib.humanize.templatetags.humanize.naturalday",
                "as_survey": "surveys.jinja2_filters.render_form",
            },
            "constants": {
                "ESTABLISHED": ESTABLISHED,
                "FAVICON_PATH": FAVICON_PATH,
                "LOGO_PATH": LOGO_PATH,
                # JS configuration
                "CSRF_COOKIE_NAME": CSRF_COOKIE_NAME,
                "SENTRY_DSN": SENTRY_DSN,
                "YANDEX_METRIKA_ID": YANDEX_METRIKA_ID,
            },
            "globals": {
                "messages": "core.jinja2.globals.messages",
                "get_menu": "core.jinja2.globals.generate_menu",
                "crispy": "core.jinja2.globals.crispy",
                # FIXME: move from django template tags
                "can_enroll_in_course": "core.templatetags.core_tags.can_enroll_in_course",
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
            str(DJANGO_ROOT_DIR / "forms" / "templates"),
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
                'core.context_processors.common_context',
                'core.context_processors.js_config',
            ),
            'debug': DEBUG
        }
    },
]
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

SECRET_KEY = env('DJANGO_SECRET_KEY')
# Sensitive model-based configuration is encrypted with this key.
# Don't forget to update site configuration after rotating a secret key.
DB_SECRET_KEY = env.str('DJANGO_DB_SECRET_KEY')


# Email settings
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = env.str('DJANGO_EMAIL_ADDRESS')
EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=465)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_SEND_COOLDOWN = 0.5
EMAIL_BACKEND = env.str('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

HASHIDS_SALT = env.str('HASHIDS_SALT')

YANDEX_DISK_USERNAME = env.str('YANDEX_DISK_USERNAME')
YANDEX_DISK_PASSWORD = env.str('YANDEX_DISK_PASSWORD')
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/"


# Default keys are taken from https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")
RECAPTCHA_USE_SSL = True

INSTALLED_APPS = [
    'modeltranslation',  # insert before admin
    'dal',
    'dal_select2',
    'core.apps.CustomAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.humanize',

    'loginas',
    'registration',
    'sorl.thumbnail',
    'crispy_forms',
    'simple_history',
    'import_export',
    'bootstrap_pagination',
    'prettyjson',
    'mptt',
    'django_rq',
    'webpack_loader',
    'django_filters',
    'rest_framework',
    'captcha',
    'taggit',

    'core.apps.CoreConfig',
    'menu',
    # django.contrib.static with a customized list of ignore patterns
    'files.apps.StaticFilesConfig',
    'files.apps.MediaFilesConfig',
    'auth.apps.AuthConfig',  # custom `User` model is defined in `users` app
    'users.apps.UsersConfig',
    'htmlpages',
    'courses.apps.CoursesConfig',
    'study_programs.apps.StudyProgramsConfig',
    'learning.apps.LearningConfig',
    'tasks',
    'learning.gallery.apps.GalleryConfig',
    'notifications.apps.NotificationsConfig',
    'api.apps.APIConfig',
    'library.apps.LibraryConfig',
]

# i18n, l10n
LANGUAGE_CODE = 'ru'
LANGUAGES = [
    ('ru', "Russian"),
    ('en', "English"),
]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [
    str(ROOT_DIR / "locale"),
]
USE_TZ = True
TIME_ZONE = 'UTC'
DATE_FORMAT = 'j E Y'
DEFAULT_TIMEZONE = pytz.timezone("Europe/Moscow")

# auth
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = (
    "auth.backends.RBACModelBackend",
)
CAN_LOGIN_AS = lambda request, target_user: request.user.is_superuser
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGINAS_FROM_USER_SESSION_FLAG = "loginas_from_user"

# TODO: remove?
CLUB_SITE_ID = 2

DEFAULT_CITY_CODE = "spb"
DEFAULT_BRANCH_CODE = "spb"
ADMIN_URL = '/narnia/'
ADMIN_REORDER: List[Any] = []
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Determine if we should apply 'selected' to parents when one of their
# children is the 'selected' menu
MENU_SELECT_PARENTS = True


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        # FIXME: Better to use more restricted rules by default
        'rest_framework.permissions.IsAuthenticatedOrReadOnly'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'UNAUTHENTICATED_USER': 'users.models.ExtendedAnonymousUser',
    # TODO: migrate all existing api views to the camel case renderer
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'JSON_UNDERSCOREIZE': {
        'no_underscore_before_number': True,
    },
    'DATE_INPUT_FORMATS': ['iso-8601', '%d.%m.%Y']
}


# CKEDITOR Settings
CKEDITOR_UPLOAD_PATH = "uploads/"  # /media/uploads/*
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_ALLOW_NONIMAGE_FILES = False
CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'contentsCss': [],
        'toolbar_YouCustomToolbarConfig': [
            {'name': 'document',
             'items': ['Source', '-', 'Preview', 'Maximize']},
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'RemoveFormat']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList']},
            {'name': 'insert', 'items': ['Image', 'Table', 'CodeSnippet']},
            {'name': 'styles', 'items': ['Format']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'clipboard',
             'items': ['-', 'Undo', 'Redo']},
            '/',  # put this to force next toolbar on new line
        ],
        'toolbar': 'YouCustomToolbarConfig',  # put selected toolbar config here
        # 'toolbarGroups': [{ 'name': 'document', 'groups': [ 'mode', 'document', 'doctools' ] }],
        # 'height': 291,
        'extraAllowedContent': 'figure(*); figcaption(figure-caption); div(*)[data-*]; span(*); p(*); th(*); td(*); section(*); ul(*); li(*); iframe[*](embed, _responsive); h1(*); h2(*)',
        'format_tags': 'p;h1;h2;h3;h4;h5',
        'width': 'calc(100% - 2px)',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        # 'toolbarCanCollapse': True,
        # 'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        'extraPlugins': ','.join(
            [
                'div',
                'autolink',
                'autoembed',
                'embedsemantic',
                'autogrow',
                # 'devtools',
                'widget',
                'lineutils',
                'clipboard',
                'dialog',
                'dialogui',
                'elementspath',
                'uploadimage',
                'codesnippet',
                # 'image2',
                # 'uploadwidget',
            ]),
    }
}

