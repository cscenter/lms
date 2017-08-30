"""
Django settings for both cscenter and csclub projects.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
from pathlib import Path

import pytz

PROJECT_DIR = Path(__file__).parents[2]
ROOT_DIR = PROJECT_DIR.parent

MEDIA_ROOT = str(PROJECT_DIR / "media")
MEDIA_URL = "/media/"

FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o775
FILE_UPLOAD_PERMISSIONS = 0o664

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = MODELTRANSLATION_DEBUG = True
THUMBNAIL_DEBUG = False

DEFAULT_CITY_CODE = "spb"
CENTER_BRANCHES_CITY_CODES = ['spb', 'nsk']
CLUB_DOMAIN = 'compsciclub.ru'
CENTER_SITE_ID = 1
CLUB_SITE_ID = 2

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(PROJECT_DIR / "templates"),
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

                'learning.context_processors.redirect_bases'
            ),
            'debug': DEBUG
        }
    },
]

INSTALLED_APPS = [
    'modeltranslation',  # insert before admin
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'core.storage.StaticFilesConfig',  # custom ignore patterns list
    'django.contrib.humanize',

    'treemenus',
    'menu_extension',
    'sorl.thumbnail',
    'crispy_forms',
    'floppyforms',
    'formtools',
    'bootstrap3',
    'taggit',
    'sitemetrics',
    'micawber.contrib.mcdjango',
    'slides',
    'dbbackup',

    'users',
    'core',
    'htmlpages',
    'learning',
    'staff',
    'library.apps.LibraryConfig',
    'loginas',
    'import_export',
    'pipeline',
    'bootstrap_pagination',
    'prettyjson',
    'mptt',
    'learning.gallery.apps.GalleryConfig',
    'learning.projects.apps.ProjectsConfig',
    'notifications.apps.NotificationsConfig',
    'rest_framework',
    'api.apps.APIConfig',
    'stats.apps.StatisticsConfig',
    'django_rq',
    'django_js_reverse',
    'webpack_loader',
    'django_filters',
]

# django-js-reverse settings
JS_REVERSE_JS_VAR_NAME = 'URLS'
JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ['api']
JS_REVERSE_OUTPUT_PATH = str(PROJECT_DIR / "assets" / "js" / "urls")

# oEmbed
MICAWBER_PROVIDERS = "learning.micawber_providers.oembed_providers"
MICAWBER_DEFAULT_SETTINGS = {
    'maxwidth': 599,
    'maxheight': 467,
    'width': 599,
    'height': 487
}

# Email settings
EMAIL_HOST = 'smtp.yandex.ru'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'dummy@dummy'
EMAIL_HOST_PASSWORD = 'dummy_password'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'cscdb',
        'USER': 'csc',
        'PASSWORD': 'FooBar',
        'HOST': 'localhost',
        'PORT': ''
        }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'ru'
LANGUAGES = [
    ('ru', "Russian"),
    ('en', "English"),
]
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = [
    str(PROJECT_DIR / "core" / "locale"),
]

USE_TZ = True
TIME_ZONE = 'UTC'
# Better to move timezone values to `City` model and cache it later
TIME_ZONES = {
    'spb': pytz.timezone('Europe/Moscow'),
    'nsk': pytz.timezone('Asia/Novosibirsk'),
    'kzn': pytz.timezone('Europe/Moscow')
}

AUTH_USER_MODEL = "users.CSCUser"
AUTHENTICATION_BACKENDS = [
    "users.backends.EmailOrUsernameModelBackend",
]
CAN_LOGIN_AS = lambda request, target_user: request.user.is_curator

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGINAS_FROM_USER_SESSION_FLAG = "loginas_from_user"

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# use dummy values to avoid accidental messing of real data
SLIDESHARE_API_KEY = "dummy_ss_key"
SLIDESHARE_SECRET = "dummy_ss_secret"
SLIDESHARE_USERNAME = "dummy_ss_username"
SLIDESHARE_PASSWORD = "dummy_ss_password"

YANDEX_DISK_USERNAME = "dummy_ya_username"
YANDEX_DISK_PASSWORD = "dummy_ya_password"
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/"

# special user with access to S3 bucket
DBBACKUP_S3_ACCESS_KEY = 'dummy_s3_access_key'
DBBACKUP_S3_SECRET_KEY = 'dummy_s3_secret_key'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = str(PROJECT_DIR / "static")
STATICFILES_DIRS = [
    str(PROJECT_DIR / "assets"),
]

# See django-pipeline for details
PIPELINE = {}
STATICFILES_STORAGE = 'core.storage.PipelineCachedGZIPedStorage'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


HASHIDS_SALT = "^TimUbi)AUwc>]B-`g2"
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# SORL settings
THUMBNAIL_DUMMY = True
# Lets store keys in redis and share them between csclub and cscenter sites
# It's safe while we store images in shared directory
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
REDIS_PASSWORD = '3MUvZ/wV{6e86jq@x4uA%RDn9KbrV#WU]A=L76J@Q9iCa*9+vN'
THUMBNAIL_REDIS_HOST = '127.0.0.1'
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD

# Make sure settings are the same as in ansible configuration
RQ_QUEUES = {
    'default': {
        'HOST': '127.0.0.1',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
    'high': {
        'HOST': '127.0.0.1',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
    'club': {
        'HOST': '127.0.0.1',
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
}


NOTIFICATION_TYPES = [
    "NEW_PROJECT_REPORT",
    "NEW_PROJECT_REPORT_COMMENT",
    # All project reports checked by curators
    "PROJECT_REPORTS_IN_REVIEW_STATE",
    "PROJECT_REPORTING_STARTED",
    "PROJECT_REPORTING_ENDED",
    "PROJECT_REVIEWER_ENROLLED",
    "PROJECT_REPORT_REVIEW_COMPLETED",
    "PROJECT_REPORT_COMPLETED",
    "NEW_ASSIGNMENT",
    "NEW_ASSIGNMENT_NEWS",
    "NEW_ASSIGNMENT_SUBMISSION",
    "ASSIGNMENT_DEADLINE_UPDATED",
    "NEW_ASSIGNMENT_SUBMISSION_COMMENT",
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'UNAUTHENTICATED_USER': 'users.models.NotAuthenticatedUser'
}

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'js/dist/',  # relative to STATIC_URL
        'STATS_FILE': str(ROOT_DIR / "webpack" / "webpack-stats.json"),
    }
}


ADMIN_REORDER = [
    ('learning', ["AreaOfStudy", "StudyProgram", "StudyProgramCourse"])
]

DATE_FORMAT = 'j E Y'
