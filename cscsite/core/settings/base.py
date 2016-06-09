"""
Django settings for both cscenter and csclub projects.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from unipath import Path

PROJECT_DIR = Path(__file__).ancestor(3)
ROOT_DIR = PROJECT_DIR.ancestor(1)

MEDIA_ROOT = PROJECT_DIR.child("media")
MEDIA_URL = "/media/"

FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o775
FILE_UPLOAD_PERMISSIONS = 0o664

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = MODELTRANSLATION_DEBUG = True
THUMBNAIL_DEBUG = False

DEFAULT_CITY_CODE = "RU SPB"
CLUB_DOMAIN = 'compsciclub.ru'
CENTER_SITE_ID = 1
CLUB_SITE_ID = 2
CITY_SESSION_KEY = CITY_COOKIE_NAME = '_city_code'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            PROJECT_DIR.child("templates"),
        ],
        'OPTIONS': {
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader'
            ),
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

INSTALLED_APPS = (
    'flat',
    'modeltranslation', # insert before admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'treemenus',
    'menu_extension',
    'sorl.thumbnail',
    'crispy_forms',
    'floppyforms',
    'bootstrap3',
    'taggit',
    'sitemetrics',
    'micawber.contrib.mcdjango',
    'slides',
    'dbbackup',

    'users',
    'core',
    'htmlpages',
    'index',
    'learning',
    'staff',
    'library',
    'loginas',
    'import_export',
    'pipeline',
    'bootstrap_pagination',
    'prettyjson',
    'mptt',
    'learning.gallery.apps.GalleryConfig'
)

# oEmbed
MICAWBER_PROVIDERS = "learning.micawber_providers.oembed_providers"

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
LANGUAGES = (
    ('ru', "Russian"),
    ('en', "English"),
)
USE_I18N = True
USE_L10N = True
LOCALE_PATHS = (
    Path(PROJECT_DIR, "core", "locale"),
)

TIME_ZONE = 'Europe/Moscow'
USE_TZ = True

AUTH_USER_MODEL = "users.CSCUser"
AUTHENTICATION_BACKENDS = (
    "users.backends.EmailOrUsernameModelBackend",
)
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
YANDEX_DISK_SLIDES_ROOT = "/dummy_ya_root"

# special user with access to S3 bucket
DBBACKUP_S3_ACCESS_KEY = 'dummy_s3_access_key'
DBBACKUP_S3_SECRET_KEY = 'dummy_s3_secret_key'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = PROJECT_DIR.child("static")

STATICFILES_DIRS = (
    PROJECT_DIR.child("assets"),
)

# See django-pipeline for details
STATICFILES_STORAGE = 'core.storage.PipelineCachedGZIPedStorage'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


HASHIDS_SALT = "^TimUbi)AUwc>]B-`g2"

# Oembed defaults
MICAWBER_DEFAULT_SETTINGS = {
    'maxwidth': 910,
    'maxheight': 512,
}

# SORL settings
THUMBNAIL_DUMMY = True
THUMBNAIL_DUMMY_SOURCE = "http://dummyimage.com/166x166/000000/ffffff&text=404+(Not+Found)"

WEBPACK_LOADER = {}