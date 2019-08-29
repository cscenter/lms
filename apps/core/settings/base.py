"""
Django settings shared between projects.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/
"""
from pathlib import Path

import pytz

ROOT_DIR = Path(__file__).parents[3]
APPS_DIR = ROOT_DIR / "apps"

MEDIA_ROOT = str(ROOT_DIR / "media")
MEDIA_URL = "/media/"
ADMIN_URL = '/narnia/'

# FIXME: or 755?
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o775
FILE_UPLOAD_PERMISSIONS = 0o664

DEBUG = False
MODELTRANSLATION_DEBUG = False
THUMBNAIL_DEBUG = False

DEFAULT_CITY_CODE = "spb"
DEFAULT_BRANCH_CODE = "spb"
DEFAULT_TIMEZONE = pytz.timezone("Europe/Moscow")

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
    'django.contrib.humanize',

    'loginas',
    'registration',
    'sorl.thumbnail',
    'crispy_forms',
    'formtools',
    'bootstrap3',
    'micawber.contrib.mcdjango',
    'dbbackup',
    'simple_history',
    'import_export',
    'bootstrap_pagination',
    'prettyjson',
    'mptt',
    'django_rq',
    'webpack_loader',
    'django_filters',
    'rest_framework',  # what about club site?
    'captcha',
    'taggit',

    'core.storage.StaticFilesConfig',  # custom list of ignore patterns
    'core.apps.CoreConfig',
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
STATICFILES_STORAGE = 'static_compress.storage.CompressedManifestStaticFilesStorage'
STATIC_COMPRESS_FILE_EXTS = ['css', 'js', 'svg']
STATIC_COMPRESS_METHODS = ['gz+zlib']
STATIC_COMPRESS_KEEP_ORIGINAL = True
STATIC_COMPRESS_MIN_SIZE_KB = 30
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Make sure settings are the same as in ansible configuration
REDIS_PASSWORD = '3MUvZ/wV{6e86jq@x4uA%RDn9KbrV#WU]A=L76J@Q9iCa*9+vN'
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
}

HASHIDS_SALT = "^TimUbi)AUwc>]B-`g2"
DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000

# sorl-thumbnails app settings
THUMBNAIL_DUMMY = True
THUMBNAIL_PRESERVE_FORMAT = True
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_REDIS_HOST = '127.0.0.1'
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD


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

# Determine if we should apply 'selected' to parents when one of their
# children is the 'selected' menu
MENU_SELECT_PARENTS = True

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

