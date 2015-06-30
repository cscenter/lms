"""
Django settings for cscsite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from unipath import Path
import os

BASE_DIR = Path(__file__).ancestor(2)
PROJECT_DIR = Path(__file__).ancestor(3)

MEDIA_ROOT = PROJECT_DIR.child("media")
MEDIA_URL = "/media/"
STATIC_ROOT = PROJECT_DIR.child("static")

STATICFILES_DIRS = (
    PROJECT_DIR.child("assets"),
)

TEMPLATE_DIRS = (
    PROJECT_DIR.child("templates"),
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'chf0ao=8=ihflu_ln2&z+jke)*cx=k0e3mzuq+pc+x+6@vxrj7'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = TEMPLATE_DEBUG = MODELTRANSLATION_DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1

EMAIL_HOST = 'smtp.yandex.ru'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'
# use dummy password to avoid accidental messing of real data
EMAIL_HOST_PASSWORD = 'dummy_password'
EMAIL_PORT = 465
# XXX remove after Django 1.7 is out.
EMAIL_BACKEND = 'crutches.compat.SSLEmailBackend'

# Application definition

INSTALLED_APPS = (
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
    'dbbackup',

    'users',
    'core',
    'htmlpages',
    'news',
    'index',
    'learning',
    'library',
    'crutches',
    'loginas',
    'pipeline',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'core.notifications.UnreadNotificationsCacheMiddleware',
)

ROOT_URLCONF = 'cscsite.urls'

WSGI_APPLICATION = 'cscsite.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',

    'core.context_processors.redirect_bases'
)

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

LANGUAGE_CODE = 'ru-RU'
LANGUAGES = (
    ('ru', "Russian"),
    ('en', "English"),
)
LOCALE_PATHS = (
    "conf/locale",
)

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

AUTH_USER_MODEL = "users.CSCUser"
AUTHENTICATION_BACKENDS = (
    "crutches.compat.EmailOrUsernameModelBackend",
)

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGINAS_FROM_USER_SESSION_FLAG = "loginas_from_user"
# this urls will be used to redirect from '/learning/' and '/teaching/'
LEARNING_BASE = 'assignment_list_student'
TEACHING_BASE = 'assignment_list_teacher'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# don't know what will happen if we change this when there are models in DB
SPRING_TERM_START = '10 jan'
SUMMER_TERM_START = '7 jul'
AUTUMN_TERM_START = '1 sep'

THUMBNAIL_DEBUG = False

# use dummy values to avoid accidental messing of real data
SLIDESHARE_API_KEY = "dummy_ss_key"
SLIDESHARE_SECRET = "dummy_ss_secret"
SLIDESHARE_USERNAME = "dummy_ss_username"
SLIDESHARE_PASSWORD = "dummy_ss_password"

YANDEX_DISK_USERNAME = "dummy_ya_username"
YANDEX_DISK_PASSWORD = "dummy_ya_password"
YANDEX_DISK_SLIDES_ROOT = "dummy_ya_root"

SOUTH_MIGRATION_MODULES = {
    'taggit': 'taggit.south_migrations',
}

# django-dbbackup settings

DBBACKUP_CLEANUP_KEEP = 30
DBBACKUP_CLEANUP_KEEP_MEDIA = 30
# FIXME(Dmitry): for now, django-dbbackup is buggy, see [1] and [2].
#                Therefore, we provide our own implementation of S3 upload,
#                so next line is commented out and backups go to /tmp
#
#                [1] https://bitbucket.org/mjs7231/django-dbbackup/issue/55/
#                [2] https://bitbucket.org/mjs7231/django-dbbackup/issue/50/
#
# DBBACKUP_STORAGE = 'dbbackup.storage.s3_storage'
CSC_TMP_BACKUP_DIR = "/tmp/cscbackup"
DBBACKUP_BACKUP_DIRECTORY = CSC_TMP_BACKUP_DIR

DBBACKUP_S3_BUCKET = 'csc-main-backup'
DBBACKUP_S3_DIRECTORY = 'cscweb_backups'
DBBACKUP_S3_DOMAIN = 's3.eu-central-1.amazonaws.com'
# special user with access to S3 bucket
DBBACKUP_S3_ACCESS_KEY = 'dummy_s3_access_key'
DBBACKUP_S3_SECRET_KEY = 'dummy_s3_secret_key'

NEWRELIC_CONF = Path(BASE_DIR.ancestor(2), "newrelic.ini")
NEWRELIC_ENV = 'development'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="


# Js/Css compression settings

# Enable versioning
STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

# Disable compression
PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.NoopCompressor'
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.NoopCompressor'

# Enable concatenation and compression.
PIPELINE_ENABLED = True

# Do not wrap js output with anonymous function
PIPELINE_DISABLE_WRAPPER = True

PIPELINE_JS = {
    'base': {
        'source_filenames': (
            'js/holder.js',
            'js/readmore.min.js',
            'js/md5.js',
            'js/EpicEditor-v0.2.2/js/epiceditor.min.js',
            # custom marked build clashes with the one in EpicEditor,
            # therefore this include should be *after* EpicEditor
            'js/marked.js',
            'js/bootstrap.min.js',
            'js/vendor/jquery.jgrowl.min.js',
            'js/main.js',
        ),
        'output_filename': 'js/dist/base.js',
    },
    'fileinput': {
        'source_filenames': (
            'js/bootstrap-fileinput/fileinput.min.js',
            'js/bootstrap-fileinput/fileinput_locale_ru.js',
            'js/bootstrap-fileinput/main.js',
        ),
        'output_filename': 'js/dist/fileinput.js',
    }
}
