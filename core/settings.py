"""
https://docs.djangoproject.com/en/2.2/topics/settings/
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

from pathlib import Path

ROOT_DIR = Path(__file__).parents[1]
APP_DIR = Path(__file__).parent

SECRET_KEY = '1zh$0zlqsd0a_o*4_e)m=%^23yzh#6w_6-6&_f@zd!2+jd&lyl'

DEBUG = True

ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = str(ROOT_DIR / "static")
ASSETS_ROOT = ROOT_DIR / "assets"
STATICFILES_DIRS = [
    str(ASSETS_ROOT),
]

MEDIA_ROOT = str(ROOT_DIR / "media")
MEDIA_URL = "/media/"


# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django_jinja',
    'treemenus',  # v1 menu
    'menu',  # v2 menu support
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'core.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(APP_DIR / "db.sqlite3"),
    }
}

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
            str(ROOT_DIR / "templates"),
            str(ASSETS_ROOT / "v2" / "dist" / "img"),  # svg inline support
        ],
        "NAME": "jinja2",
        "OPTIONS": {
            "match_extension": ".jinja2",
            "extensions": [
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "jinja2.ext.with_",
                "jinja2.ext.i18n",
                "jinja2.ext.autoescape",
                "django_jinja.builtins.extensions.CsrfExtension",
                "django_jinja.builtins.extensions.CacheExtension",
                "django_jinja.builtins.extensions.TimezoneExtension",
                "django_jinja.builtins.extensions.UrlsExtension",
                "django_jinja.builtins.extensions.StaticFilesExtension",
                "django_jinja.builtins.extensions.DjangoFiltersExtension",
                "webpack_loader.contrib.jinja2ext.WebpackExtension",
                "core.jinja2_extensions.MessagesExtension",
                "core.jinja2_extensions.MenuExtension",
            ],
            "bytecode_cache": {
                "name": "default",
                "backend": "django_jinja.cache.BytecodeCache",
                "enabled": False,
            },
            "newstyle_gettext": True,
            "autoescape": True,
            "auto_reload": DEBUG,
            "translation_engine": "django.utils.translation",
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(ROOT_DIR / "templates"),
            str(ROOT_DIR / "assets" / "v2" / "dist" / "img"),  # svg inline support
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
            ),
            'debug': DEBUG
        }
    },
]

AUTH_USER_MODEL = "core.User"
LOGOUT_REDIRECT_URL = '/'

WSGI_APPLICATION = 'core.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'v1/dist/.local/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(ASSETS_ROOT / "v1" / "dist" / ".local" / "webpack-stats-v1.json"),
    },
    'V2': {
        'BUNDLE_DIR_NAME': 'v2/dist/.local/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(ASSETS_ROOT / "v2" / "dist" / ".local" / "webpack-stats-v2.json"),
    }
}
