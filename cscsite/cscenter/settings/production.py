# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .base import *

DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG

ALLOWED_HOSTS = ["compscicenter.ru", "www.compscicenter.ru", "*"]

MEDIA_ROOT = Path('/shared', 'media')

# Logging-related stuff
RAVEN_CONFIG = {
    # Note(lebedev): see https://app.getsentry.com/cscenter/cscenter/docs/django
    # for instructions.
    "dsn": "https://7d2d63dd1ba84e149d2cf42e21179dfb:825f3d7218284ab3a7334ff5d2077e02@app.getsentry.com/13763"
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache'
    }
}

INSTALLED_APPS += ('raven.contrib.django.raven_compat', )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': True,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

EMAIL_HOST_PASSWORD = '***REMOVED***'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# -- learning
SLIDESHARE_API_KEY = "E3GDS7t4"
SLIDESHARE_SECRET = "fnk6fOLp"
SLIDESHARE_USERNAME = "compscicenter"
SLIDESHARE_PASSWORD = "vorobey"

YANDEX_DISK_USERNAME = "csc-slides@yandex.ru"
YANDEX_DISK_PASSWORD = "***REMOVED***"
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/2015-2016"


# django-dbbackup settings
DBBACKUP_STORAGE = 'dbbackup.storage.s3_storage'
DBBACKUP_STORAGE_OPTIONS = {
    'location': PROJECT_DIR.child("backups"),
    'bucket_name': 'cscenter',
    'host': 's3.eu-central-1.amazonaws.com',
    'access_key': '***REMOVED***',
    'secret_key': '***REMOVED***',
    'calling_format': 'boto.s3.connection.OrdinaryCallingFormat'
}
DBBACKUP_DATE_FORMAT = '%d-%m-%Y-%H'
DBBACKUP_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'
DBBACKUP_MEDIA_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'

NEWRELIC_ENV = 'production'

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
