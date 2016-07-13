import sys

from .base import *


INSTALLED_APPS += ['fixture_media',
                   'debug_toolbar',
                   'django_extensions',
                   'template_timings_panel',
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

FLAMES_DIR = PROJECT_DIR.parent.child("flame_graph")

ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

THUMBNAIL_DEBUG = True

EMAIL_HOST = '127.0.0.1'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'simple'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'learning.management.imports': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'DEBUG',
        },
        'learning.models': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'DEBUG',
        },
    },
}

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'bundles/',
        'STATS_FILE': PROJECT_DIR.child("webpack-stats-local.json"),
        'IGNORE': ['.+\.hot-update.js', '.+\.map']
    }
}

SLIDESHARE_API_KEY = "OX5YoPYg"
SLIDESHARE_SECRET = "R3lITlTK"
SLIDESHARE_USERNAME = "pacahon"
SLIDESHARE_PASSWORD = "q3wcp001"
