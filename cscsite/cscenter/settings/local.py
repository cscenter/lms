import sys

from .base import *

DEBUG_TOOLBAR_PATCH_SETTINGS = False
MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware'
] + MIDDLEWARE
INTERNAL_IPS = ["127.0.0.1", "::1"]

INSTALLED_APPS += ['debug_toolbar',
                   'django_extensions',
                   # 'template_timings_panel',
                   'rosetta']

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    # 'template_timings_panel.panels.TemplateTimings.TemplateTimings',
    # 'djdt_flamegraph.FlamegraphPanel',
]


FLAMES_DIR = PROJECT_DIR.parent / "flame_graph"

ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

THUMBNAIL_DEBUG = True

EMAIL_HOST = '127.0.0.1'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'sql': {
            '()': 'core.utils.SQLFormatter',
            'format': '[%(duration).3f] %(statement)s',
        },
        "rq_console": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        "rq_console": {
            "level": "DEBUG",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "rq_console",
            "exclude": ["%(asctime)s"],
        },
        'sql': {
            'class': 'logging.StreamHandler',
            'formatter': 'sql',
            'level': 'DEBUG',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # root logger
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends.schema': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'notifications.handlers': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        "notifications.notifier": {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        "rq.worker": {
            "handlers": ["rq_console"],
            "level": "DEBUG",
            'propagate': False,
        },
        "post_office": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400

SLIDESHARE_API_KEY = "OX5YoPYg"
SLIDESHARE_SECRET = "R3lITlTK"
SLIDESHARE_USERNAME = "pacahon"
SLIDESHARE_PASSWORD = "q3wcp001"

THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.cached_db_kvstore.KVStore'

# Disable django-debug-toolbar jquery
DEBUG_TOOLBAR_CONFIG = {
    # 'SHOW_TOOLBAR_CALLBACK': lambda r: False,  # disables it
}

LDAP_CLIENT_URI = "ldap://review.compscicenter.ru:389"
LDAP_DB_SUFFIX = "dc=review,dc=compscicenter,dc=ru"
LDAP_CLIENT_USERNAME = "admin"
LDAP_CLIENT_PASSWORD = "superStrongPassword"
LDAP_TLS_TRUSTED_CA_CERT_FILE = "/Users/jetbrains/Downloads/tmp/trustedCA.crt"
LDAP_SYNC_PASSWORD = True

GERRIT_API_URI = "https://review.compscicenter.ru/a/"
GERRIT_CLIENT_USERNAME = "admin"
GERRIT_CLIENT_PASSWORD = "OOR4UvAgcPSHl37mWvjHeCioB6W1r/lzQvs6+CU3Wg"
