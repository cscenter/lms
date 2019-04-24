"""
CS center app specific settings
"""
import django

from core.settings.base import *

SITE_ID = 1
WSGI_APPLICATION = 'compscicenter_ru.wsgi.application'
ROOT_URLCONF = 'compscicenter_ru.urls'
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
    LMS_SUBDOMAIN: 'my_compscicenter_ru.urls',
}
PROJECT_DIR = Path(__file__).parents[1]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'core.middleware.CurrentCityMiddleware',
    'subdomains.middleware.SubdomainURLRoutingMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'users.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'learning.middleware.StudentCityMiddleware',
    'core.middleware.RedirectMiddleware',
]
INSTALLED_APPS += [
    'compscicenter_ru',
    'my_compscicenter_ru',
    'menu',
    'post_office',
    'django_jinja',
    'learning.projects.apps.ProjectsConfig',
    'stats.apps.StatisticsConfig',
    'admission.apps.AdmissionConfig',
    'staff',
    'surveys.apps.SurveysConfig',
    'online_courses.apps.Config',
    'learning.internships.apps.InternshipsConfig',
    'publications.apps.PublicationsConfig',
    'ckeditor',
    'ckeditor_uploader',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    },
    'social_networks': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(ROOT_DIR / ".cache")
    }
}

# Oauth settings for getting access to login from Yandex.Passport
# Note: application managed under `contest@compscicenter.ru` user
SOCIAL_AUTH_YANDEXRU_KEY = "9990b75d62a541f88812b6ce8b39574f"
SOCIAL_AUTH_YANDEXRU_SECRET = "7fd828cbb49d49d7a57b242828ea7115"
# Note: we prevent calling pipeline for this backend
SOCIAL_AUTH_YANDEXRU_PIPELINE = []

# Add site specific templates
TEMPLATES = [
    {
        "BACKEND": "django_jinja.backend.Jinja2",
        "APP_DIRS": False,
        'DIRS': [
            django.__path__[0] + '/forms/jinja2',
            str(ROOT_DIR / "compscicenter_ru" / "jinja2"),
            str(ROOT_DIR / "my_compscicenter_ru" / "jinja2"),
            # FIXME: move to apps/jinja2 ?
            str(APPS_DIR / "core" / "jinja2"),
            str(APPS_DIR / "surveys" / "jinja2"),
            # svg inline support
            str(APPS_DIR / "assets" / "v2" / "dist" / "img"),
        ],
        "NAME": "jinja2",
        "OPTIONS": {
            "match_extension": None,
            "match_regex": r"^(?!narnia/).*",
            # Or put filters under templatetags and load with
            # django-jinja decorator
            "filters": {
                "markdown": "compscicenter_ru.jinja2_filters.markdown",
                "as_survey": "surveys.jinja2_filters.render_form",
            },
            "globals": {
                "crispy": "compscicenter_ru.jinja2_filters.crispy",
            },
            "extensions": [
                "jinja2.ext.do",
                "jinja2.ext.loopcontrols",
                "jinja2.ext.with_",
                "jinja2.ext.i18n",
                "jinja2.ext.autoescape",
                "pipeline.jinja2.PipelineExtension",
                "django_jinja.builtins.extensions.CsrfExtension",
                "django_jinja.builtins.extensions.CacheExtension",
                "django_jinja.builtins.extensions.TimezoneExtension",
                "django_jinja.builtins.extensions.StaticFilesExtension",
                "django_jinja.builtins.extensions.DjangoFiltersExtension",
                "webpack_loader.contrib.jinja2ext.WebpackExtension",
                "compscicenter_ru.jinja2_extensions.Extensions",
                "compscicenter_ru.jinja2_extensions.UrlsExtension",
                "compscicenter_ru.jinja2_extensions.MenuExtension",
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
            str(PROJECT_DIR / "templates"),
            str(APPS_DIR / "surveys" / "jinja2"),
            str(PROJECT_DIR / "apps" / "admission" / "templates"),
            str(APPS_DIR / "staff" / "templates"),
            str(APPS_DIR / "templates"),
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
            ),
            'debug': DEBUG
        }
    },
]
FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

LOCALE_PATHS += [
    str(PROJECT_DIR / "locale"),
    str(APPS_DIR / "learning" / "projects" / "locale"),
    str(PROJECT_DIR / "apps" / "admission" / "locale"),
    str(APPS_DIR / "surveys" / "locale"),
]
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'chf0ao=8=ihflu_ln2&z+jke)*cx=k0e3mzuq+pc+x+6@vxrj7'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = 'development'


AWS_SES_ACCESS_KEY_ID = ''
AWS_SES_SECRET_ACCESS_KEY = ''
AWS_SES_REGION_NAME = 'eu-west-1'
AWS_SES_REGION_ENDPOINT = 'email.eu-west-1.amazonaws.com'
POST_OFFICE = {
    'BACKENDS': {
        'ses': 'django.core.mail.backends.console.EmailBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}


LDAP_CLIENT_URI = "ldap:///"
LDAP_DB_SUFFIX = "dc=review,dc=compscicenter,dc=ru"
LDAP_CLIENT_USERNAME = ""
LDAP_CLIENT_PASSWORD = ""
LDAP_TLS_TRUSTED_CA_CERT_FILE = None
LDAP_SYNC_PASSWORD = False


# Stub
ADMIN_REORDER = []


MENU_SELECT_PARENTS = True

# Share this cookie between subdomains
SESSION_COOKIE_NAME = "cscsessionid"
SESSION_COOKIE_DOMAIN = ".compscicenter.ru"


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
            {'name': 'clipboard',
             'items': ['-', 'Undo', 'Redo']},
            {'name': 'insert', 'items': ['Image', 'Table', 'CodeSnippet']},
            {'name': 'styles', 'items': ['Format']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
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
