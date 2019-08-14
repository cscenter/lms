"""
Django settings shared between projects.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/
"""
from pathlib import Path

import pytz

from django.utils.translation import ugettext_lazy as _

ROOT_DIR = Path(__file__).parents[3]
APPS_DIR = ROOT_DIR / "apps"

MEDIA_ROOT = str(ROOT_DIR / "media")
MEDIA_URL = "/media/"

# FIXME: or 755?
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o775
FILE_UPLOAD_PERMISSIONS = 0o664

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = MODELTRANSLATION_DEBUG = True
THUMBNAIL_DEBUG = False

DEFAULT_CITY_CODE = "spb"
CENTER_BRANCHES_CITY_CODES = ['spb', 'nsk']

CITIES = {
    "spb": _("Saint Petersburg"),
    "nsk": _("Novosibirsk")
}
CLUB_DOMAIN = 'compsciclub.ru'
CENTER_SITE_ID = 1
CLUB_SITE_ID = 2

CSRF_COOKIE_NAME = 'csrf_token'

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
    'core.storage.StaticFilesConfig',  # custom list of ignore patterns
    'django.contrib.humanize',

    'auth.apps.AuthConfig',  # custom `User` model is defined in `users` app
    'loginas',
    'registration',
    'users.apps.UsersConfig',
    'sorl.thumbnail',
    'crispy_forms',
    'formtools',
    'bootstrap3',
    'micawber.contrib.mcdjango',
    'dbbackup',
    'simple_history',

    'import_export',
    'pipeline',
    'bootstrap_pagination',
    'prettyjson',
    'mptt',
    'django_rq',
    'webpack_loader',
    'django_filters',
    'rest_framework',  # what about club site?

    'core',
    'htmlpages',
    'courses.apps.CoursesConfig',
    'study_programs.apps.StudyProgramsConfig',
    'learning.apps.LearningConfig',
    'tasks',
    'learning.gallery.apps.GalleryConfig',
    'notifications.apps.NotificationsConfig',
    'api.apps.APIConfig',
    # FIXME: quick fix, error on user detail page
    'taggit',  # used by library app only
    'library.apps.LibraryConfig',
    'captcha',
]

# oEmbed
MICAWBER_PROVIDERS = "courses.micawber_providers.oembed_providers"
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
    str(ROOT_DIR / "locale"),
]

USE_TZ = True
TIME_ZONE = 'UTC'
# Better to move timezone values to `City` model and cache it later
TIME_ZONES = {
    'spb': pytz.timezone('Europe/Moscow'),
    'nsk': pytz.timezone('Asia/Novosibirsk'),
    'kzn': pytz.timezone('Europe/Moscow'),
    'online': pytz.timezone('Europe/Moscow'),
}

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = (
    "auth.backends.RBACModelBackend",
)
CAN_LOGIN_AS = lambda request, target_user: request.user.is_curator

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGINAS_FROM_USER_SESSION_FLAG = "loginas_from_user"

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# use dummy values to avoid accidental messing of real data
YANDEX_DISK_USERNAME = "dummy_ya_username"
YANDEX_DISK_PASSWORD = "dummy_ya_password"
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/"

# special user with access to S3 bucket
DBBACKUP_S3_ACCESS_KEY = 'dummy_s3_access_key'
DBBACKUP_S3_SECRET_KEY = 'dummy_s3_secret_key'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = str(APPS_DIR / "static")
STATICFILES_DIRS = [
    str(APPS_DIR / "assets"),
]

# See django-pipeline for details
PIPELINE = {}
STATICFILES_STORAGE = 'core.storage.PipelineCachedGZIPedStorage'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


HASHIDS_SALT = "***REMOVED***"
DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000

# SORL settings
THUMBNAIL_DUMMY = True
THUMBNAIL_PRESERVE_FORMAT = True
# Lets store keys in redis and share them between csclub and cscenter sites
# It's safe while we store images in shared directory
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
REDIS_PASSWORD = None
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

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'UNAUTHENTICATED_USER': 'users.models.ExtendedAnonymousUser',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'v1/dist/',  # relative to STATIC_URL
        'STATS_FILE': str(ROOT_DIR / "public" / "webpack-stats.json"),
    },
    'V2': {
        'BUNDLE_DIR_NAME': 'v2/dist/',
        'STATS_FILE': str(ROOT_DIR / "public" / "webpack-stats-v2.json"),
    }
}

DATE_FORMAT = 'j E Y'

# Presume foundation year starts from spring term
FOUNDATION_YEAR = 2007
CENTER_FOUNDATION_YEAR = 2011


# Recaptcha settings
NOCAPTCHA = True
RECAPTCHA_USE_SSL = True
