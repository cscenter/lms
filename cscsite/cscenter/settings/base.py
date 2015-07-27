"""
Django settings for cscenter project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from unipath import Path

BASE_DIR = Path(__file__).ancestor(2)
PROJECT_DIR = Path(__file__).ancestor(3)

MEDIA_ROOT = PROJECT_DIR.child("media")
MEDIA_URL = "/media/"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = TEMPLATE_DEBUG = MODELTRANSLATION_DEBUG = True

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

                'core.context_processors.redirect_bases'
            )
            # TEMPLATE_DEBUG deprecated, but still usefull then `debug` here
        }
    },
]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

ALLOWED_HOSTS = []

SITE_ID = 1

EMAIL_HOST = 'smtp.yandex.ru'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'
# use dummy password to avoid accidental messing of real data
EMAIL_HOST_PASSWORD = 'dummy_password'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

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
    'staff',
    'library',
    'crutches',
    'loginas',
    'import_export',
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

ROOT_URLCONF = 'cscenter.urls'

WSGI_APPLICATION = 'cscenter.wsgi.application'


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
    Path(BASE_DIR, "locale"),
)

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True




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
SUMMER_TERM_START = '1 jul'
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

NEWRELIC_CONF = Path(BASE_DIR, "newrelic.ini")
NEWRELIC_ENV = 'development'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = PROJECT_DIR.child("static")

STATICFILES_DIRS = (
    PROJECT_DIR.child("assets"),
)

# See django-pipeline for details
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
            'js/vendor/holder.js',
            'js/vendor/readmore.min.js',
            'js/vendor/md5.js',
            'js/vendor/EpicEditor-v0.2.2/js/epiceditor.min.js',
            # custom marked build clashes with the one in EpicEditor,
            # therefore this include should be *after* EpicEditor
            'js/vendor/marked.js',
            'js/vendor/bootstrap.min.js',
            'js/vendor/jquery.jgrowl.min.js',
            'js/main.js',
        ),
        'output_filename': 'js/dist/base.js',
    },
    'fileinput': {
        'source_filenames': (
            'js/vendor/bootstrap-fileinput/fileinput.min.js',
            'js/vendor/bootstrap-fileinput/fileinput_locale_ru.js',
            'js/teaching-sheet__fileinput.js',
        ),
        'output_filename': 'js/dist/fileinput.js',
    }
}
