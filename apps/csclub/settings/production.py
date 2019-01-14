# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .base import *

DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG

ALLOWED_HOSTS = [".compsciclub.ru"]

MEDIA_ROOT = str(Path('/shared', 'media'))

# Logging-related stuff
RAVEN_CONFIG = {
    # Note(lebedev): see https://app.getsentry.com/cscenter/cscenter/docs/django
    # for instructions.
    "dsn": "https://8e585e0a766b4a8786870813ed7a4be4:143a5566340f4955a257151f2199c3e5@app.getsentry.com/13763"
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache_club'
    }
}

INSTALLED_APPS += ['raven.contrib.django.raven_compat',]

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
        'django.template': {
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

EMAIL_HOST_PASSWORD = 'XgpWN4CzBGqCbNsb8'

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# -- learning
SLIDESHARE_API_KEY = "E3GDS7t4"
SLIDESHARE_SECRET = "fnk6fOLp"
SLIDESHARE_USERNAME = "compscicenter"
SLIDESHARE_PASSWORD = "vorobey"

YANDEX_DISK_USERNAME = "csc-slides@yandex.ru"
YANDEX_DISK_PASSWORD = "***REMOVED***"


# django-dbbackup settings
DBBACKUP_CLEANUP_KEEP = 30
DBBACKUP_CLEANUP_KEEP_MEDIA = 30
CSC_TMP_BACKUP_DIR = "/tmp/csclub_backup"
DBBACKUP_BACKUP_DIRECTORY = CSC_TMP_BACKUP_DIR

DBBACKUP_S3_BUCKET = 'csclub'
DBBACKUP_S3_DIRECTORY = 'cscweb_backups'
DBBACKUP_S3_DOMAIN = 's3.eu-central-1.amazonaws.com'
# Access Key for csclub backup user
DBBACKUP_S3_ACCESS_KEY = 'AKIAJWPKEDQ6YJEPKFFQ'
DBBACKUP_S3_SECRET_KEY = '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'

NEWRELIC_ENV = 'production'

REDIS_PASSWORD = '***REMOVED***'
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD
for queue in RQ_QUEUES.values():
    if 'PASSWORD' in queue:
        queue['PASSWORD'] = REDIS_PASSWORD
