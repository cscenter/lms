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
    "dsn": "https://8e585e0a766b4a8786870813ed7a4be4:143a5566340f4955a257151f2199c3e5@app.getsentry.com/13763"
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache'
    }
}

INSTALLED_APPS += ['raven.contrib.django.raven_compat',]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
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
        '': {
            'level': 'WARNING',
            'handlers': ['sentry'],
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.template': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': True,
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
        "rq.worker": {
            "handlers": ["console"],
            "level": "WARNING",
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

EMAIL_HOST_PASSWORD = 'P@ssw0rd238'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# -- learning
SLIDESHARE_API_KEY = "E3GDS7t4"
SLIDESHARE_SECRET = "fnk6fOLp"
SLIDESHARE_USERNAME = "compscicenter"
SLIDESHARE_PASSWORD = "vorobey"

YANDEX_DISK_USERNAME = "csc-slides@yandex.ru"
YANDEX_DISK_PASSWORD = "deelthisat"


# django-dbbackup settings
DBBACKUP_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DBBACKUP_STORAGE_OPTIONS = {
    'location': '/',
    'bucket_name': 'cscenter',
    'region_name': 'eu-central-1',
    'access_key': 'AKIAJMQIFB2CNXR65ALQ',
    'secret_key': '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',
}
DBBACKUP_TMP_DIR = '/shared/backup_tmp'
DBBACKUP_DATE_FORMAT = '%d-%m-%Y-%H'
DBBACKUP_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'
DBBACKUP_MEDIA_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'

NEWRELIC_ENV = 'production'

AWS_SES_ACCESS_KEY_ID = 'AKIAJZ44WHPOEURR4TZA'
AWS_SES_SECRET_ACCESS_KEY = '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'
