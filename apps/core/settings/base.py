"""
Django settings shared between projects.
"""
from pathlib import Path

import pytz

ROOT_DIR = Path(__file__).parents[3]
SHARED_APPS_DIR = ROOT_DIR / "apps"

ADMIN_URL = '/narnia/'

DEFAULT_CITY_CODE = "spb"
DEFAULT_BRANCH_CODE = "spb"
DEFAULT_TIMEZONE = pytz.timezone("Europe/Moscow")

# FIXME: remove
CLUB_SITE_ID = 2

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
    'micawber.contrib.mcdjango',
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

# oEmbed
MICAWBER_PROVIDERS = "courses.micawber_providers.oembed_providers"
MICAWBER_DEFAULT_SETTINGS = {
    'maxwidth': 599,
    'maxheight': 467,
    'width': 599,
    'height': 487
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
DATE_FORMAT = 'j E Y'

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = (
    "auth.backends.RBACModelBackend",
)
CAN_LOGIN_AS = lambda request, target_user: request.user.is_superuser
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGINAS_FROM_USER_SESSION_FLAG = "loginas_from_user"

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# https://docs.djangoproject.com/en/2.2/howto/static-files/
ASSETS_ROOT = ROOT_DIR / "assets"
STATICFILES_DIRS = [
    str(ASSETS_ROOT),
]
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000

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
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

WEBPACK_LOADER = {
    'V1': {
        'BUNDLE_DIR_NAME': 'v1/dist/prod/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(ROOT_DIR / "webpack-stats-v1.json"),
    },
    'V2': {
        'BUNDLE_DIR_NAME': 'v2/dist/prod/',
        'STATS_FILE': str(ROOT_DIR / "webpack-stats-v2.json"),
    }
}


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
