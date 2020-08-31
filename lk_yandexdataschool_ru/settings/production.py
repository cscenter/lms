import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

# STATICFILES_STORAGE = 'files.storage.CloudFrontManifestStaticFilesStorage'
CDN_SOURCE_STATIC_URL = STATIC_URL
# CDN_STATIC_URL = 'https://resources.compscicenter.ru/'
# STATIC_URL = CDN_STATIC_URL
# for webpack_config in WEBPACK_LOADER.values():
#    webpack_config['LOADER_CLASS'] = 'core.webpack_loader.BundleDirectoryWebpackLoader'

# Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[sentry_logging, DjangoIntegration()]
)


CACHES['default'] = {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': '/tmp/django_cache'
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        "rq.worker": {
            "handlers": ["console"],
            "level": "WARNING",
            'propagate': False,
        },
        "post_office": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

POST_OFFICE = {
    'LOG_LEVEL': 1,  # Log only failed emails
    'BACKENDS': {
        'ses': 'django_ses.SESBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}
