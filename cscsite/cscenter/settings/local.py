import sys

from .base import *



INSTALLED_APPS += ('fixture_media',
                   'debug_toolbar',
                   'django_extensions',
                   'template_timings_panel',
                   'rosetta')

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
    'template_timings_panel.panels.TemplateTimings.TemplateTimings',
]

FLAMES_DIR = PROJECT_DIR.parent.child("flame_graph")
MIDDLEWARE_CLASSES += ('core.middleware.FlamesMiddleware',)

ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

THUMBNAIL_DEBUG = True

EMAIL_HOST = '127.0.0.1'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

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
        'learning.utils': {
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

# Looks for files in PIPELINE_CSS and PIPELINE_JS
STATICFILES_FINDERS += (
    'pipeline.finders.ManifestFinder',
)

# Only concatenate files for debug purpose
PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.NoopCompressor'
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.NoopCompressor'

# Versioning disabled if DEBUG=True
PIPELINE_ENABLED = False


FILE_UPLOAD_HANDLERS = (
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)
