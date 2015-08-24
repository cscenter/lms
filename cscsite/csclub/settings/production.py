# -*- coding: utf-8 -*-

from __future__ import absolute_import

from unipath import Path

from .base import *

TEMPLATE_DEBUG = DEBUG = False

ALLOWED_HOSTS = ["compsciclub.ru", "www.compsciclub.ru", "*"]

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
YANDEX_DISK_SLIDES_ROOT = "/CSCenterMaterials/2014-2015"


# django-dbbackup settings
DBBACKUP_CLEANUP_KEEP = 30
DBBACKUP_CLEANUP_KEEP_MEDIA = 30
# FIXME(Dmitry): for now, django-dbbackup is buggy, see [1] and [2].
#                Therefore, we provide our own implementation of S3 upload,
#                so next line is commented out and backups go to /tmp
#
#                [1] https://bitbucket.org/mjs7231/django-dbbackup/issue/55/
#                [2] https://bitbucket.org/mjs7231/django-dbbackup/issue/50/
#
# DBBACKUP_STORAGE = 'dbbackup.storage.s3_storage'
CSC_TMP_BACKUP_DIR = "/tmp/csclub_backup"
DBBACKUP_BACKUP_DIRECTORY = CSC_TMP_BACKUP_DIR

DBBACKUP_S3_BUCKET = 'csclub'
DBBACKUP_S3_DIRECTORY = 'cscweb_backups'
DBBACKUP_S3_DOMAIN = 's3.eu-central-1.amazonaws.com'
# Access Key for csclub backup user
DBBACKUP_S3_ACCESS_KEY = 'AKIAJWPKEDQ6YJEPKFFQ'
DBBACKUP_S3_SECRET_KEY = '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'

NEWRELIC_ENV = 'production'

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
